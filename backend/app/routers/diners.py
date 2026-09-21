# -*- coding: utf-8 -*-
"""干饭成员（用餐人）路由：每人维护口味偏好 tags（口味/忌口/辣度）。

口味筛选交互：前端选中某人自动勾其 tags，多选并集 → 用这组标签过滤推荐。
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlite3 import Connection

from app.db import get_db, jdump, row_to_dict

router = APIRouter(prefix="/diners", tags=["diners"])


class DinerIn(BaseModel):
    name: str
    tags: List[str] = []


class TagsIn(BaseModel):
    tags: List[str] = []


def _get(conn: Connection, did: int):
    row = conn.execute("SELECT * FROM diners WHERE id=?", (did,)).fetchone()
    if not row:
        raise HTTPException(404, "干饭成员不存在")
    return row_to_dict(row)


@router.get("")
def list_diners(conn: Connection = Depends(get_db)):
    rows = conn.execute("SELECT * FROM diners ORDER BY id").fetchall()
    return [row_to_dict(r) for r in rows]


@router.post("")
def create_diner(body: DinerIn, conn: Connection = Depends(get_db)):
    cur = conn.execute(
        "INSERT INTO diners(name,tags) VALUES(?,?)",
        (body.name, jdump(body.tags)),
    )
    return {"id": cur.lastrowid, "ok": True}


@router.get("/{did}")
def get_diner(did: int, conn: Connection = Depends(get_db)):
    return _get(conn, did)


@router.put("/{did}")
def update_diner(did: int, body: DinerIn, conn: Connection = Depends(get_db)):
    _get(conn, did)
    conn.execute(
        "UPDATE diners SET name=?, tags=? WHERE id=?",
        (body.name, jdump(body.tags), did),
    )
    return {"id": did, "ok": True}


@router.put("/{did}/tags")
def update_diner_tags(did: int, body: TagsIn, conn: Connection = Depends(get_db)):
    """仅更新某成员的口味标签（心情变色等场景用）。"""
    _get(conn, did)
    conn.execute("UPDATE diners SET tags=? WHERE id=?", (jdump(body.tags), did))
    return {"id": did, "tags": body.tags, "ok": True}


@router.delete("/{did}")
def delete_diner(did: int, conn: Connection = Depends(get_db)):
    conn.execute("DELETE FROM diners WHERE id=?", (did,))
    return {"id": did, "ok": True}