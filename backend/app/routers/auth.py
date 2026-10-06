# -*- coding: utf-8 -*-
"""
auth 路由：微信小程序登录 + JWT 鉴权中间件。

登录流程（小程序端）：
  1. 前端 wx.login() 拿到 code
  2. POST /auth/login  body={ "code": "xxx" }
  3. 后端用 code + appid + appsecret 调微信 code2session → 拿到 openid
  4. upsert users 表（按 openid 查重）→ 建/取 user
  5. 返回 { user_id, nickname, token }

鉴权：
  所有业务路由 header 带  Authorization: Bearer <token>
  token 格式:  "<user_id>.<timestamp>.<hmac签名>"
  后端依赖 get_current_user() 解析出 user_id，替换掉原来硬编码的 Query(1)
"""
import base64
import hashlib
import hmac
import json
import time
import urllib.parse
import urllib.request
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from ..db import get_conn

router = APIRouter(prefix="/auth", tags=["auth"])

# token 有效期 30 天
TOKEN_TTL = 30 * 24 * 3600
# 如果 configs 表里没配 secret，用这个兜底（首次启动还没填的时候能用）
_FALLBACK_JWT_SECRET = "eatwhat-dev-secret-change-me"


# ---------------------------------------------------------------------------
# JWT 极简实现：user_id.timestamp.hmac_sha256
# 不引 pyjwt，用标准库 hmac，够安全够用
# ---------------------------------------------------------------------------
def _jwt_secret(conn) -> str:
    """从 configs 表取 jwt_secret，没配就用 fallback。"""
    row = conn.execute("SELECT value FROM configs WHERE key='jwt_secret'").fetchone()
    if row and row["value"]:
        return row["value"]
    return _FALLBACK_JWT_SECRET


def sign_token(conn, user_id: int) -> str:
    ts = int(time.time())
    payload = f"{user_id}.{ts}"
    secret = _jwt_secret(conn)
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()[:16]
    return f"{payload}.{sig}"


def verify_token(conn, token: str) -> Optional[int]:
    """返回 user_id，非法或过期返回 None。"""
    parts = token.strip().split(".")
    if len(parts) != 3:
        return None
    try:
        uid, ts_str, sig = parts
        uid = int(uid)
        ts = int(ts_str)
    except (ValueError, TypeError):
        return None
    if time.time() - ts > TOKEN_TTL:
        return None
    secret = _jwt_secret(conn)
    expected = hmac.new(secret.encode(), f"{uid}.{ts}".encode(), hashlib.sha256).hexdigest()[:16]
    if not hmac.compare_digest(expected, sig):
        return None
    return uid


# ---------------------------------------------------------------------------
# 依赖：从 Authorization header 解 user_id
# ---------------------------------------------------------------------------
async def get_current_user(request: Request, conn=Depends(get_conn)) -> int:
    """严格鉴权：缺 token 或无效 → 401。"""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    uid = verify_token(conn, auth[7:])
    if uid is None:
        raise HTTPException(status_code=401, detail="token 无效或已过期")
    return uid


async def get_optional_user(request: Request, conn=Depends(get_conn)) -> int:
    """宽松鉴权：有 token 就解，没有就返回默认 user_id=1（H5 / 管理端还没接登录时用）。"""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        uid = verify_token(conn, auth[7:])
        if uid is not None:
            return uid
    return 1


# ---------------------------------------------------------------------------
# 微信 code2session
# ---------------------------------------------------------------------------
def _wx_code2session(code: str, appid: str, secret: str) -> Optional[dict]:
    """用 code 换 openid/session_key/unionid。返回 JSON dict，失败返回 None。"""
    url = (
        "https://api.weixin.qq.com/sns/jscode2session"
        f"?appid={urllib.parse.quote(appid)}"
        f"&secret={urllib.parse.quote(secret)}"
        f"&js_code={urllib.parse.quote(code)}"
        "&grant_type=authorization_code"
    )
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read().decode())
    except Exception:
        return None
    if "openid" in data:
        return data
    return None


# ---------------------------------------------------------------------------
# 登录接口
# ---------------------------------------------------------------------------
class LoginBody(BaseModel):
    code: str
    nickname: Optional[str] = None
    avatar: Optional[str] = None


class LoginOut(BaseModel):
    user_id: int
    nickname: str
    avatar: str
    token: str
    is_new: bool


@router.post("/login", response_model=LoginOut)
def login(body: LoginBody, conn=Depends(get_conn)):
    """
    微信小程序登录。code 由 wx.login() 产生，前端可顺带传 nickname + avatar。
    开发期（没配 mp_appid/secret）直接 mock 一个临时 openid，方便调式。
    """
    # 1. 读配置
    cfg = {
        row["key"]: row["value"]
        for row in conn.execute("SELECT key, value FROM configs WHERE key IN ('mp_appid','mp_secret')").fetchall()
    }
    appid = cfg.get("mp_appid", "")
    secret = cfg.get("mp_secret", "")

    # 2. code2session（没配或调不通 → mock，方便开发期本地跑）
    wx_data = None
    if appid and secret:
        wx_data = _wx_code2session(body.code, appid, secret)

    if wx_data:
        openid = wx_data.get("openid")
        unionid = wx_data.get("unionid", "")
    else:
        # Mock：把 code 当成伪 openid（取前 28 字符），开发期够用
        openid = f"dev_{body.code[:28]}"
        unionid = ""

    # 3. upsert users 表
    now = int(time.time())
    row = conn.execute("SELECT * FROM users WHERE openid=?", (openid,)).fetchone()
    is_new = False
    if row:
        uid = row["id"]
        # 更新 nickname/avatar（前端新版 chooseAvatar + nickname input 会传）
        nickname = body.nickname or row["nickname"] or f"吃货{uid}"
        avatar = body.avatar or row["avatar"] or ""
        conn.execute(
            "UPDATE users SET nickname=?, avatar=?, unionid=?, last_seen=? WHERE id=?",
            (nickname, avatar, unionid, now, uid),
        )
    else:
        nickname = body.nickname or f"吃货{conn.execute('SELECT COUNT(*) FROM users').fetchone()[0] + 1}"
        avatar = body.avatar or ""
        cur = conn.execute(
            "INSERT INTO users(name, openid, unionid, nickname, avatar, role, created_at, last_seen) "
            "VALUES('',?,?,?,?, 'user', ?, ?)",
            (openid, unionid, nickname, avatar, now, now),
        )
        uid = cur.lastrowid
        is_new = True
    conn.commit()

    # 4. 签 token
    token = sign_token(conn, uid)
    return LoginOut(
        user_id=uid,
        nickname=nickname,
        avatar=avatar,
        token=token,
        is_new=is_new,
    )


# ---------------------------------------------------------------------------
# 用户资料更新（前端改了头像/昵称时调）
# ---------------------------------------------------------------------------
class ProfileIn(BaseModel):
    nickname: Optional[str] = None
    avatar: Optional[str] = None


@router.put("/profile")
def update_profile(
    body: ProfileIn,
    uid: int = Depends(get_current_user),
    conn=Depends(get_conn),
):
    """更新当前用户的昵称/头像。"""
    cols, vals = [], []
    if body.nickname is not None:
        cols.append("nickname=?")
        vals.append(body.nickname.strip()[:20])
    if body.avatar is not None:
        cols.append("avatar=?")
        vals.append(body.avatar)
    if not cols:
        raise HTTPException(status_code=400, detail="无更新字段")
    vals.append(uid)
    conn.execute(f"UPDATE users SET {','.join(cols)} WHERE id=?", vals)
    conn.commit()
    row = conn.execute("SELECT id, nickname, avatar FROM users WHERE id=?", (uid,)).fetchone()
    return dict(row)


@router.get("/me")
def get_me(uid: int = Depends(get_current_user), conn=Depends(get_conn)):
    """获取当前登录用户信息。"""
    row = conn.execute("SELECT id, nickname, avatar, role FROM users WHERE id=?", (uid,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="用户不存在")
    return dict(row)


# 导出 get_current_user 给其他路由用
__all__ = ["get_current_user", "router"]
