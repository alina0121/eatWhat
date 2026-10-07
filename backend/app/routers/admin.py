# -*- coding: utf-8 -*-
"""
管理端路由（仅管理公共资源，不含用户个人数据）：
- /admin/login: 密码登录（passcode 存配置表 admin_passcode），仅门控管理端，不影响移动端。
- /admin/stats: 公共资源计数（用户/参考菜谱/食材/大类/封面/技巧等），个人数据不上管理端。
- /admin/users 用户管理：新增/改名/切换角色/删除。

设计要点：
- 管理端只管公共信息；我的菜谱/冰箱/干饭/体重/餐厅收藏等个人数据一律不在此暴露，看个人数据去用户端。
- 鉴权只保护管理端入口，移动端/其余全 API 不设登录门槛（MVP 语义）。
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlite3 import Connection

from app.db import get_db, row_to_dict
from app.routers.configs import get_config
from app.routers.auth import sign_token, get_write_user

router = APIRouter(prefix="/admin", tags=["admin"])


class LoginIn(BaseModel):
    code: str


class UserIn(BaseModel):
    name: str
    role: str = "user"      # user | admin


class UserPatch(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None


@router.post("/login")
def admin_login(body: LoginIn, conn: Connection = Depends(get_db)):
    """校验管理端口令，并签发一个「管理台令牌」。

    管理台与用户端复用同一套写接口；写接口现在要求登录，管理台靠这个令牌
    （放在 X-Admin-Token header 里）通过鉴权，用户端登录态不受任何影响。
    """
    pwd = get_config(conn, "admin_passcode", "123456")
    if body.code != pwd:
        raise HTTPException(401, "口令错误")
    row = conn.execute(
        "SELECT id FROM users WHERE role='admin' ORDER BY id LIMIT 1"
    ).fetchone()
    admin_uid = row["id"] if row else 1
    return {"ok": True, "token": sign_token(conn, admin_uid), "user_id": admin_uid}


@router.get("/stats")
def admin_stats(conn: Connection = Depends(get_db)):
    """公共资源计数（不含任何个人数据）。"""
    def cnt(sql, *args):
        return conn.execute(sql, args).fetchone()[0]

    return {
        "cards": {
            "users": cnt("SELECT COUNT(*) FROM users"),
            "recipes_ref": cnt("SELECT COUNT(*) FROM recipes WHERE source='admin'"),
            "ingredients": cnt("SELECT COUNT(*) FROM ingredients"),
            "categories": cnt("SELECT COUNT(*) FROM categories"),
            "tips_total": cnt("SELECT COUNT(*) FROM tips"),
            "tips_pending": cnt("SELECT COUNT(*) FROM tips WHERE status='pending'"),
        }
    }


def _get_user(conn: Connection, uid: int):
    row = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    if not row:
        raise HTTPException(404, "用户不存在")
    return row_to_dict(row)


@router.get("/users")
def list_users(conn: Connection = Depends(get_db)):
    """用户列表。"""
    rows = conn.execute("SELECT * FROM users ORDER BY id").fetchall()
    return [row_to_dict(r) for r in rows]


@router.post("/users")
def create_user(body: UserIn, conn: Connection = Depends(get_db), _admin: int = Depends(get_write_user)):
    """新增用户。"""
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "名称不能为空")
    if conn.execute("SELECT id FROM users WHERE name=?", (name,)).fetchone():
        raise HTTPException(409, "已存在同名用户")
    # name 与 nickname 同步写入：展示名统一以后端 nickname 为准
    # （微信/邮箱登录也只写 nickname），否则新增的用户在各处都显示不出名字
    cur = conn.execute(
        "INSERT INTO users(name,nickname,role) VALUES(?,?,?)", (name, name, body.role)
    )
    return {"id": cur.lastrowid, "ok": True}


@router.put("/users/{uid}")
def update_user(uid: int, body: UserPatch, conn: Connection = Depends(get_db),
                _admin: int = Depends(get_write_user)):
    """改名 / 切换角色。

    安全规则：
    - 不能把「自己」降级为普通用户（admin → user），否则管理端会自锁死；
    - 内置演示管理员 id=1 不可降级（前端已有 disabled 样式，后端再次兜底）。
    改名 / 改别人的角色不受限。
    """
    target = _get_user(conn, uid)
    data = body.model_dump(exclude_none=True)

    # —— 角色降级拦截 ——
    if "role" in data and data["role"] != "admin":
        # 自己不能把自己踢下台（否则管理端只剩自己一个 admin，把自己降了就全锁死）
        if uid == _admin:
            raise HTTPException(403, "不能把自己降级为普通用户")
        # 注：「目标是 admin 就永远不让降级」不做硬拦截——管理员数量必须是运营决策，但自降级必须锁死；
        # 真要降别的 admin，另一个管理员可以，避免多管理员场景下某个 admin 被永久锁为 admin。

    if "name" in data:
        data["name"] = data["name"].strip()
        if not data["name"]:
            raise HTTPException(400, "名称不能为空")
        if conn.execute(
            "SELECT id FROM users WHERE name=? AND id IS NOT ?",
            (data["name"], uid),
        ).fetchone():
            raise HTTPException(409, "已存在同名用户")
        # 同步 nickname：展示名以后端 nickname 为准（微信/邮箱登录也只写它），
        # 否则管理端改完名字，用户列表/「我的」页仍显示旧名或不显示
        data["nickname"] = data["name"]
    if not data:
        raise HTTPException(400, "没有可更新的字段")
    sets = ", ".join(f"{k}=?" for k in data)
    conn.execute(f"UPDATE users SET {sets} WHERE id=?", (*data.values(), uid))
    return {"id": uid, "ok": True}


@router.delete("/users/{uid}")
def delete_user(uid: int, conn: Connection = Depends(get_db),
                _admin: int = Depends(get_write_user)):
    """删除用户。

    安全规则：
    - 内置演示管理员 id=1 不可删（原始约束，前后端一致）；
    - 不能删除「自己」，否则管理端会自锁死（无管理员可用）。
    """
    if uid == 1:
        raise HTTPException(400, "内置管理员不可删除")
    if uid == _admin:
        raise HTTPException(403, "不能删除自己")
    _get_user(conn, uid)
    conn.execute("DELETE FROM users WHERE id=?", (uid,))
    return {"id": uid, "ok": True}