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
    """校验管理端口令。通过返回 ok，前端存会话标记解锁管理台。"""
    pwd = get_config(conn, "admin_passcode", "123456")
    if body.code != pwd:
        raise HTTPException(401, "口令错误")
    return {"ok": True}


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
            "covers": cnt("SELECT COUNT(*) FROM covers"),
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
def create_user(body: UserIn, conn: Connection = Depends(get_db)):
    """新增用户。"""
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "名称不能为空")
    if conn.execute("SELECT id FROM users WHERE name=?", (name,)).fetchone():
        raise HTTPException(409, "已存在同名用户")
    cur = conn.execute(
        "INSERT INTO users(name,role) VALUES(?,?)", (name, body.role)
    )
    return {"id": cur.lastrowid, "ok": True}


@router.put("/users/{uid}")
def update_user(uid: int, body: UserPatch, conn: Connection = Depends(get_db)):
    """改名 / 切换角色。"""
    _get_user(conn, uid)
    data = body.model_dump(exclude_none=True)
    if "name" in data:
        data["name"] = data["name"].strip()
        if not data["name"]:
            raise HTTPException(400, "名称不能为空")
        if conn.execute(
            "SELECT id FROM users WHERE name=? AND id IS NOT ?",
            (data["name"], uid),
        ).fetchone():
            raise HTTPException(409, "已存在同名用户")
    if not data:
        raise HTTPException(400, "没有可更新的字段")
    sets = ", ".join(f"{k}=?" for k in data)
    conn.execute(f"UPDATE users SET {sets} WHERE id=?", (*data.values(), uid))
    return {"id": uid, "ok": True}


@router.delete("/users/{uid}")
def delete_user(uid: int, conn: Connection = Depends(get_db)):
    """删除用户（保留演示管理员 id=1，不可删）。"""
    if uid == 1:
        raise HTTPException(400, "内置管理员不可删除")
    _get_user(conn, uid)
    conn.execute("DELETE FROM users WHERE id=?", (uid,))
    return {"id": uid, "ok": True}