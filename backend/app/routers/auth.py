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
import logging
import time
import urllib.parse
import urllib.request
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from ..db import get_conn

router = APIRouter(prefix="/auth", tags=["auth"])

logger = logging.getLogger(__name__)

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
    """宽松鉴权：有 token 就解出真实 user_id，没有则返回 0。

    0 = 未登录游客，不是任何真实账号：业务表里不存在 user_id=0 的历史数据，
    所以未登录时各页天然是空态。这里绝不能回退到 1 号 —— 那会把 1 号账号
    （管理员）的冰箱/口味标签等私人数据端给未登录的人看。
    """
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        uid = verify_token(conn, auth[7:])
        if uid is not None:
            return uid
    return 0


# ---------------------------------------------------------------------------
# 写操作鉴权：未登录禁止新增 / 修改 / 删除
# ---------------------------------------------------------------------------
# PC 管理台没有用户账号（靠口令进入），与用户端复用同一套写接口。
# 这里让管理台登录后额外带一个管理员令牌 header，与用户 token 并行不悖：
# 用户端登录态完全不受影响，管理台也能继续管理公共资源。
ADMIN_TOKEN_HEADER = "X-Admin-Token"


def _admin_uid(request: Request, conn) -> Optional[int]:
    """校验管理台令牌：有效且该用户 role=admin 才认。否则返回 None。"""
    tok = request.headers.get(ADMIN_TOKEN_HEADER, "")
    if not tok:
        return None
    uid = verify_token(conn, tok)
    if uid is None:
        return None
    row = conn.execute("SELECT role FROM users WHERE id=?", (uid,)).fetchone()
    if row and row["role"] == "admin":
        return uid
    return None


async def get_write_user(request: Request, conn=Depends(get_conn)) -> int:
    """写操作依赖：必须已登录（用户 token），或持有效管理台令牌。

    未登录（既没有有效用户 token，也不是管理台）一律 401 —— 未登录只能浏览
    公开内容（参考菜谱 / 已公开技巧等），不能新增 / 修改 / 删除。
    读接口继续用 get_optional_user（游客 user_id=0，各页天然空态）。
    """
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        uid = verify_token(conn, auth[7:])
        if uid is not None and uid > 0:
            return uid
    auid = _admin_uid(request, conn)
    if auid is not None:
        return auid
    raise HTTPException(status_code=401, detail="请先登录后再操作")


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
    # 开发期用：小程序前端首次启动生成一个 uuid 存 storage，wx.login 时连同 code 一起传过来，
    # 没配 mp_appid/secret 时用这个稳定 uuid 当 mock openid，避免每次 code 变 → 每次新建账号。
    mock_openid: Optional[str] = None


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
        # Mock：优先用前端传来的固定 mock_openid（storage 持久化，开发期稳定）；
        # 没传的兜底回退到 dev_<code[:28]>（每次 code 变会新建，留着做安全兜底）
        if body.mock_openid and len(body.mock_openid) <= 40:
            openid = f"dev_{body.mock_openid}"
        else:
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
    """获取当前登录用户信息（含绑定邮箱，前端「我的」页展示用）。"""
    row = conn.execute("SELECT id, nickname, avatar, role, email FROM users WHERE id=?", (uid,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="用户不存在")
    return dict(row)


# 导出 get_current_user 给其他路由用
__all__ = ["get_current_user", "router"]

# ===========================================================================
# 邮箱验证码登录 / 绑定 / 注销
# ===========================================================================
import re as _re
import sys as _sys
_sys.path.insert(0, str(_sys.path[0]))
from ..email import generate_otp, send_otp_email, is_smtp_configured

_EMAIL_RE = _re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]{2,}$')


def _validate_email(email: str) -> bool:
    return bool(email and _EMAIL_RE.match(email.strip()))


def _consume_otp(conn, email: str, code: str, purpose: str):
    """校验验证码 + 标记已用。返回 (是否通过, 失败原因)。

    失败原因必须区分「已过期 / 已被用 / 填错了」：
    只回一句「验证码错误或已过期」时，用户根本分不清是自己手输错了还是邮件来晚了，
    本次线上问题就是这么被误判成「一收到就过期」的。
    """
    now = int(time.time())
    row = conn.execute(
        "SELECT * FROM email_otps WHERE email=? AND purpose=? AND code=? AND used=0 AND expired_at>?",
        (email, purpose, code, now),
    ).fetchone()
    if row:
        conn.execute("UPDATE email_otps SET used=1 WHERE id=?", (row["id"],))
        return True, ""

    # 未命中 → 逐层定位原因，给用户一句能照做的提示
    hit = conn.execute(
        "SELECT used, expired_at FROM email_otps WHERE email=? AND purpose=? AND code=? "
        "ORDER BY id DESC LIMIT 1",
        (email, purpose, code),
    ).fetchone()
    if hit:
        if hit["used"]:
            return False, "该验证码已经用过了，请重新获取"
        return False, "验证码已过期，请点击「获取验证码」拿新的"

    # 这个码在库里不存在 → 看该邮箱最近一次发的码是否已过期
    latest = conn.execute(
        "SELECT expired_at FROM email_otps WHERE email=? AND purpose=? ORDER BY id DESC LIMIT 1",
        (email, purpose),
    ).fetchone()
    if latest is None:
        return False, "请先点击「获取验证码」"
    if latest["expired_at"] <= now:
        return False, "验证码已过期，请点击「获取验证码」拿新的"
    return False, "验证码不正确，请核对邮件里的 6 位数字"


# ---------------------------------------------------------------------------
# 1. 发验证码
# ---------------------------------------------------------------------------
class SendOtpBody(BaseModel):
    email: str
    purpose: str = "login"   # login | bind | reset


class SendOtpOut(BaseModel):
    ok: bool
    hint: str


@router.post("/send-email-code", response_model=SendOtpOut)
def send_email_code(body: SendOtpBody, conn=Depends(get_conn)):
    email = body.email.strip().lower()
    purpose = body.purpose if body.purpose in ("login", "bind", "reset") else "login"

    if not _validate_email(email):
        raise HTTPException(400, "邮箱格式不正确")

    # 频控：同邮箱 60 秒内只能发一次
    last = conn.execute(
        "SELECT created_at FROM email_otps WHERE email=? ORDER BY id DESC LIMIT 1",
        (email,),
    ).fetchone()
    if last and int(time.time()) - last["created_at"] < 60:
        raise HTTPException(429, "发验证码太频繁，请 60 秒后再试")

    # 绑定场景：邮箱必须未被其他用户占用
    if purpose == "bind":
        existing = conn.execute(
            "SELECT id FROM users WHERE email=? AND email!=''", (email,)
        ).fetchone()
        if existing:
            raise HTTPException(409, "该邮箱已被其他账号绑定")

    # 登录场景：邮箱被绑 → 正常发；没被绑 → 也能发（自动注册）
    code = generate_otp()
    expire_min = int(
        conn.execute("SELECT value FROM configs WHERE key='otp_expire_min'").fetchone()[0]
        or 10
    )
    now = int(time.time())
    conn.execute(
        "INSERT INTO email_otps(email, code, purpose, expired_at, used, created_at) "
        "VALUES(?,?,?,?,0,?)",
        (email, code, purpose, now + expire_min * 60, now),
    )
    conn.commit()

    send_otp_email(conn, email, code, purpose)

    smtp_ok = is_smtp_configured(conn)
    hint = "验证码已发送" if smtp_ok else "验证码已生成（SMTP 未配置，见后端日志）"
    return SendOtpOut(ok=True, hint=hint)


# ---------------------------------------------------------------------------
# 2. 邮箱验证码登录 / 自动注册
# ---------------------------------------------------------------------------
class EmailLoginBody(BaseModel):
    email: str
    code: str
    nickname: Optional[str] = None


@router.post("/login-email", response_model=LoginOut)
def login_email(body: EmailLoginBody, conn=Depends(get_conn)):
    email = body.email.strip().lower()
    if not _validate_email(email):
        raise HTTPException(400, "邮箱格式不正确")
    if not body.code or len(body.code) != 6:
        raise HTTPException(400, "请输入 6 位验证码")

    ok, reason = _consume_otp(conn, email, body.code, "login")
    if not ok:
        # 记下用户实际提交的邮箱+验证码，排查「收到码却说无效」时一眼能看出差在哪
        logger.warning(
            f"[auth] 登录验证码校验失败 email={email} code={body.code} reason={reason}"
        )
        raise HTTPException(400, reason)

    # 找/建用户
    now = int(time.time())
    row = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    is_new = False
    if row:
        uid = row["id"]
        nickname = body.nickname or row["nickname"] or f"吃货{uid}"
        conn.execute(
            "UPDATE users SET nickname=?, last_seen=? WHERE id=?", (nickname, now, uid)
        )
    else:
        # 新用户：openid 用 "email_" + 哈希，和微信用户区分开
        import hashlib
        fake_openid = "email_" + hashlib.md5(email.encode()).hexdigest()[:24]
        nickname = body.nickname or f"吃货{conn.execute('SELECT COUNT(*) FROM users').fetchone()[0] + 1}"
        cur = conn.execute(
            "INSERT INTO users(name, openid, email, nickname, role, created_at, last_seen) "
            "VALUES('',?,?,?, 'user', ?, ?)",
            (fake_openid, email, nickname, now, now),
        )
        uid = cur.lastrowid
        is_new = True
    conn.commit()
    token = sign_token(conn, uid)
    return LoginOut(
        user_id=uid, nickname=nickname, avatar="", token=token, is_new=is_new
    )


# ---------------------------------------------------------------------------
# 3. 绑定邮箱
# ---------------------------------------------------------------------------
class BindEmailBody(BaseModel):
    email: str
    code: str


@router.post("/bind-email")
def bind_email(body: BindEmailBody, uid: int = Depends(get_current_user), conn=Depends(get_conn)):
    email = body.email.strip().lower()
    if not _validate_email(email):
        raise HTTPException(400, "邮箱格式不正确")

    # 检查是否已绑定其他邮箱
    cur = conn.execute("SELECT email FROM users WHERE id=?", (uid,)).fetchone()
    if cur and cur["email"]:
        raise HTTPException(400, f"当前账号已绑定 {cur['email']}，请先解绑")

    # 检查邮箱是否被别人用了
    dup = conn.execute(
        "SELECT id FROM users WHERE email=? AND id!=? AND email!=''", (email, uid)
    ).fetchone()
    if dup:
        raise HTTPException(409, "该邮箱已被其他账号绑定")

    # 验证验证码（purpose=bind）
    ok, reason = _consume_otp(conn, email, body.code, "bind")
    if not ok:
        logger.warning(
            f"[auth] 绑定邮箱验证码校验失败 uid={uid} email={email} code={body.code} reason={reason}"
        )
        raise HTTPException(400, reason)

    conn.execute("UPDATE users SET email=? WHERE id=?", (email, uid))
    conn.commit()
    row = conn.execute("SELECT id, email FROM users WHERE id=?", (uid,)).fetchone()
    return {"ok": True, "email": row["email"]}


# ---------------------------------------------------------------------------
# 4. 解绑邮箱
# ---------------------------------------------------------------------------
@router.post("/unbind-email")
def unbind_email(uid: int = Depends(get_current_user), conn=Depends(get_conn)):
    cur = conn.execute("SELECT email FROM users WHERE id=?", (uid,)).fetchone()
    if not cur or not cur["email"]:
        raise HTTPException(400, "当前账号未绑定邮箱")
    conn.execute("UPDATE users SET email='' WHERE id=?", (uid,))
    conn.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# 5. 注销账户（物理删除用户所有数据 + 自身）
# ---------------------------------------------------------------------------
# 所有带 user_id 的业务表，注销时级联清理（表名必须与 db.py 实际建表一致）
_CASCADE_TABLES = [
    "recipes", "shops", "diners", "records", "weights", "tips",
    "fridge_items", "purchase", "eat_inbox",
    "categories", "ingredients", "taste_tags",
]


@router.delete("/me")
def delete_my_account(uid: int = Depends(get_current_user), conn=Depends(get_conn)):
    """
    注销账户：物理删除该用户所有数据 + users 表记录。
    前端必须弹两次确认（文字输入「确认注销」或双弹 confirm），这里不做校验，
    前端拦好再调。
    """
    # 不能删管理员（防止误操作把管理端搞挂）
    user = conn.execute("SELECT role FROM users WHERE id=?", (uid,)).fetchone()
    if user and user["role"] == "admin":
        raise HTTPException(403, "管理员账户不支持自助注销")

    # 1. 先清该用户候选挂的计时（tracks 只有 inbox_id，删 eat_inbox 前先摘掉）
    conn.execute(
        "DELETE FROM tracks WHERE inbox_id IN (SELECT id FROM eat_inbox WHERE user_id=?)",
        (uid,),
    )

    # 2. 级联删除所有业务表数据
    deleted_counts = {}
    for table in _CASCADE_TABLES:
        try:
            cur = conn.execute(f"DELETE FROM {table} WHERE user_id=?", (uid,))
            if cur.rowcount:
                deleted_counts[table] = cur.rowcount
        except Exception:
            # 表不存在或没 user_id 列 → 跳过
            pass

    # 3. 删 users 记录
    conn.execute("DELETE FROM users WHERE id=?", (uid,))
    conn.commit()

    # 4. 清本地 token（前端会在收到 200 后自动清）
    return {"ok": True, "deleted": deleted_counts, "user_id": uid}


# 更新 __all__ 导出
__all__ = ["get_current_user", "get_optional_user", "get_write_user", "router"]
