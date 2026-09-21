# -*- coding: utf-8 -*-
"""
封面图库路由：管理员维护的固定封面（emoji + 渐变主题）。

菜谱编辑时从中点选一个（写 recipes.cover = 封面 id），渲染时用对应该封面的
emoji 作菜示图、grad 作背景。删除封面时，引用它的菜谱封面回退为空（默认轮换）。

对齐食材大类的维护模式：增删改 + 上下移动排序。
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlite3 import Connection

from app.db import get_db, row_to_dict

router = APIRouter(prefix="/covers", tags=["covers"])


class CoverIn(BaseModel):
    emoji: str = "🍽"
    name: str = ""
    grad: str = "linear-gradient(135deg,#4b3fe3,#8b5cf6)"


class CoverMove(BaseModel):
    dir: str = "down"  # up | down


@router.get("")
def list_covers(conn: Connection = Depends(get_db)):
    """封面清单（按 sort 升序，供菜谱编辑点选 / 管理员维护）。"""
    rows = conn.execute(
        "SELECT * FROM covers ORDER BY sort, id"
    ).fetchall()
    return [row_to_dict(r) for r in rows]


@router.post("")
def create_cover(body: CoverIn, conn: Connection = Depends(get_db)):
    """新增封面；排到末尾。"""
    _max = conn.execute("SELECT COALESCE(MAX(sort),-1) FROM covers").fetchone()[0]
    cur = conn.execute(
        "INSERT INTO covers(emoji,name,grad,sort) VALUES(?,?,?,?)",
        (body.emoji or "🍽", body.name, body.grad, _max + 1),
    )
    return {"id": cur.lastrowid, "ok": True}


@router.put("/{cid}")
def update_cover(cid: int, body: CoverIn, conn: Connection = Depends(get_db)):
    """编辑封面（改 emoji / 色调名 / 渐变）。"""
    if not conn.execute("SELECT 1 FROM covers WHERE id=?", (cid,)).fetchone():
        raise HTTPException(404, "封面不存在")
    conn.execute(
        "UPDATE covers SET emoji=?, name=?, grad=? WHERE id=?",
        (body.emoji or "🍽", body.name, body.grad, cid),
    )
    return {"id": cid, "ok": True}


@router.post("/{cid}/move")
def move_cover(cid: int, body: CoverMove, conn: Connection = Depends(get_db)):
    """上下移动排序：与该方向相邻的封面交换 sort。"""
    row = conn.execute("SELECT * FROM covers WHERE id=?", (cid,)).fetchone()
    if not row:
        raise HTTPException(404, "封面不存在")
    direction = -1 if body.dir == "up" else 1
    cmp = ">" if direction == 1 else "<"
    nxt = conn.execute(
        f"SELECT * FROM covers WHERE sort {cmp} ? ORDER BY sort {'ASC' if direction == 1 else 'DESC'} LIMIT 1",
        (row["sort"],),
    ).fetchone()
    if not nxt:
        return {"id": cid, "ok": True}  # 已在边界
    conn.execute("UPDATE covers SET sort=? WHERE id=?", (nxt["sort"], cid))
    conn.execute("UPDATE covers SET sort=? WHERE id=?", (row["sort"], nxt["id"]))
    return {"id": cid, "ok": True}


@router.delete("/{cid}")
def delete_cover(cid: int, conn: Connection = Depends(get_db)):
    """删除封面；引用它的菜谱封面回退为空（渲染走默认轮换），不丢菜谱。"""
    if not conn.execute("SELECT 1 FROM covers WHERE id=?", (cid,)).fetchone():
        raise HTTPException(404, "封面不存在")
    conn.execute("UPDATE recipes SET cover='' WHERE cover=?", (str(cid),))
    conn.execute("DELETE FROM covers WHERE id=?", (cid,))
    return {"id": cid, "ok": True}