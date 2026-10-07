# -*- coding: utf-8 -*-
"""
口味标签路由：按 user_id 隔离。CRUD 全量自己的标签。
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlite3 import Connection
from typing import List
import json

from app.db import get_db, row_to_dict
from .auth import get_optional_user, get_write_user

router = APIRouter(prefix="/taste-tags", tags=["taste-tags"])


class TagIn(BaseModel):
    name: str


@router.get("")
def list_tags(user: int = Depends(get_optional_user), db: Connection = Depends(get_db)):
    rows = db.execute(
        "SELECT id,name,sort FROM taste_tags WHERE user_id=? ORDER BY sort ASC, id ASC",
        (user,),
    ).fetchall()
    return [row_to_dict(r) for r in rows]


@router.post("")
def create(body: TagIn, user: int = Depends(get_write_user), db: Connection = Depends(get_db)):
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(400, "标签名不能为空")
    exist = db.execute(
        "SELECT id FROM taste_tags WHERE user_id=? AND name=?", (user, name)
    ).fetchone()
    if exist:
        raise HTTPException(409, f"已有「{name}」标签")
    max_sort = db.execute(
        "SELECT COALESCE(MAX(sort), -1) FROM taste_tags WHERE user_id=?", (user,)
    ).fetchone()[0]
    new_sort = (max_sort or -1) + 1
    cur = db.execute(
        "INSERT INTO taste_tags(user_id,name,sort) VALUES(?,?,?)",
        (user, name, new_sort),
    )
    db.commit()
    return {"id": cur.lastrowid, "name": name, "sort": new_sort}


@router.put("/{tid}")
def update(tid: int, body: TagIn, user: int = Depends(get_write_user), db: Connection = Depends(get_db)):
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(400, "标签名不能为空")
    row = db.execute("SELECT * FROM taste_tags WHERE id=?", (tid,)).fetchone()
    if not row or row["user_id"] != user:
        raise HTTPException(404, "标签不存在")
    dup = db.execute(
        "SELECT id FROM taste_tags WHERE user_id=? AND name=? AND id!=?", (user, name, tid)
    ).fetchone()
    if dup:
        raise HTTPException(409, f"已有「{name}」标签")
    db.execute("UPDATE taste_tags SET name=? WHERE id=?", (name, tid))
    db.commit()
    return {"id": tid, "name": name}


@router.delete("/{tid}")
def delete(tid: int, user: int = Depends(get_write_user), db: Connection = Depends(get_db)):
    row = db.execute("SELECT * FROM taste_tags WHERE id=?", (tid,)).fetchone()
    if not row or row["user_id"] != user:
        raise HTTPException(404, "标签不存在")
    name = row["name"]
    # 校验：只查当前用户自己的菜谱/成员是否在用这个标签（别人的用法与我无关）
    used_by = []
    for r in db.execute(
        "SELECT name, tags FROM recipes WHERE user_id=?", (user,)
    ).fetchall():
        try:
            tags = json.loads(r["tags"] or "[]")
            if name in tags: used_by.append(f"菜谱「{r['name']}」")
        except Exception: pass
    for d in db.execute(
        "SELECT name, tags FROM diners WHERE user_id=?", (user,)
    ).fetchall():
        try:
            tags = json.loads(d["tags"] or "[]")
            if name in tags: used_by.append(f"成员「{d['name']}」")
        except Exception: pass
    if used_by:
        raise HTTPException(409, f"「{name}」正在被 {used_by[0]} 使用，不能删除")
    db.execute("DELETE FROM taste_tags WHERE id=?", (tid,))
    db.commit()
    return {"ok": True}


@router.put("/reorder")
def reorder(body: List[int], user: int = Depends(get_write_user), db: Connection = Depends(get_db)):
    """按传入 id 数组顺序重排 sort"""
    for i, tid in enumerate(body):
        row = db.execute("SELECT user_id FROM taste_tags WHERE id=?", (tid,)).fetchone()
        if not row or row["user_id"] != user:
            continue
        db.execute("UPDATE taste_tags SET sort=? WHERE id=?", (i, tid))
    db.commit()
    return {"ok": True}
