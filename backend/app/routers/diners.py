# -*- coding: utf-8 -*-
"""干饭成员（用餐人）路由：每人维护口味偏好 tags（口味/忌口/辣度）。

口味筛选交互：前端选中某人自动勾其 tags，多选并集 → 用这组标签过滤推荐。
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlite3 import Connection

from app.db import get_db, jdump, row_to_dict
from app.routers.auth import get_optional_user, get_write_user
from app.wxsec import check_text

router = APIRouter(prefix="/diners", tags=["diners"])


class DinerIn(BaseModel):
    name: str
    tags: List[str] = []


class TagsIn(BaseModel):
    tags: List[str] = []


def _get(conn: Connection, did: int, user: int):
    """取干饭成员并校验归属：成员按人隔离，只能看/改自己的。"""
    row = conn.execute("SELECT * FROM diners WHERE id=?", (did,)).fetchone()
    if not row or row["user_id"] != user:
        raise HTTPException(404, "干饭成员不存在")
    return row_to_dict(row)


@router.get("")
def list_diners(user: int = Depends(get_optional_user),
                conn: Connection = Depends(get_db)):
    """当前用户的干饭成员。未登录（user=0）为空。"""
    rows = conn.execute(
        "SELECT * FROM diners WHERE user_id=? ORDER BY id", (user,)
    ).fetchall()
    return [row_to_dict(r) for r in rows]


@router.post("")
def create_diner(body: DinerIn,
                 user: int = Depends(get_write_user),
                 conn: Connection = Depends(get_db)):
    # 成员名是用户输入文本，一并送内容安全检测（启用时）
    ok, reason = check_text(conn, body.name)
    if not ok:
        raise HTTPException(400, reason)
    cur = conn.execute(
        "INSERT INTO diners(user_id,name,tags) VALUES(?,?,?)",
        (user, body.name, jdump(body.tags)),
    )
    return {"id": cur.lastrowid, "ok": True}


@router.get("/{did}")
def get_diner(did: int,
              user: int = Depends(get_optional_user),
              conn: Connection = Depends(get_db)):
    return _get(conn, did, user)


@router.put("/{did}")
def update_diner(did: int, body: DinerIn,
                 user: int = Depends(get_write_user),
                 conn: Connection = Depends(get_db)):
    _get(conn, did, user)
    ok, reason = check_text(conn, body.name)
    if not ok:
        raise HTTPException(400, reason)
    conn.execute(
        "UPDATE diners SET name=?, tags=? WHERE id=?",
        (body.name, jdump(body.tags), did),
    )
    return {"id": did, "ok": True}


@router.put("/{did}/tags")
def update_diner_tags(did: int, body: TagsIn,
                      user: int = Depends(get_write_user),
                      conn: Connection = Depends(get_db)):
    """仅更新某成员的口味标签（心情变色等场景用）。"""
    _get(conn, did, user)
    conn.execute("UPDATE diners SET tags=? WHERE id=?", (jdump(body.tags), did))
    return {"id": did, "tags": body.tags, "ok": True}


@router.delete("/{did}")
def delete_diner(did: int,
                 user: int = Depends(get_write_user),
                 conn: Connection = Depends(get_db)):
    _get(conn, did, user)
    conn.execute("DELETE FROM diners WHERE id=?", (did,))
    return {"id": did, "ok": True}