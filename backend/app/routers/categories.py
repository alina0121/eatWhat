# -*- coding: utf-8 -*-
"""
食材大类路由：独立维护的实体（name/icon/sort），供食材库、冰箱、编菜谱动态引用。

约定：
- 各食物表（ingredients / fridge_items）以「大类名」关联分类。
- 改名 → 级联更新这些表里的 cat，保证数据一致。
- 删除 → 该大类下的项退回兜底「其他」（不存在则创建），不丢数据。
- 顺序 → 通过 sort 字段维护，提供上移/下移接口。
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlite3 import Connection

from app.db import get_db, row_to_dict

router = APIRouter(prefix="/categories", tags=["categories"])

FALLBACK_CAT = "其他"  # 删除大类后的兜底归类


class CategoryIn(BaseModel):
    name: str
    icon: str = "🥗"


class CategoryMove(BaseModel):
    dir: str = "down"  # up | down


def _ensure_fallback(conn: Connection) -> None:
    """保证兜底大类「其他」存在（删除兜底大类时重新兜底到它，自举修复）。"""
    if conn.execute("SELECT 1 FROM categories WHERE name=?", (FALLBACK_CAT,)).fetchone() is None:
        conn.execute(
            "INSERT INTO categories(name,icon,sort) VALUES(?,?,0)",
            (FALLBACK_CAT, "🥗"),
        )


@router.get("")
def list_categories(conn: Connection = Depends(get_db)):
    """分类清单（按 sort 升序，供前端分组与下拉）。"""
    rows = conn.execute(
        "SELECT * FROM categories ORDER BY sort, id"
    ).fetchall()
    return [row_to_dict(r) for r in rows]


@router.post("")
def create_category(body: CategoryIn, conn: Connection = Depends(get_db)):
    """新增大类；同名 409；排到末尾。"""
    name = body.name.strip()
    if not name:
        raise HTTPException(422, "名称不能为空")
    if conn.execute("SELECT 1 FROM categories WHERE name=?", (name,)).fetchone():
        raise HTTPException(409, "该大类已存在")
    _max = conn.execute("SELECT COALESCE(MAX(sort),-1) FROM categories").fetchone()[0]
    cur = conn.execute(
        "INSERT INTO categories(name,icon,sort) VALUES(?,?,?)",
        (name, body.icon or "🥗", _max + 1),
    )
    return {"id": cur.lastrowid, "ok": True}


@router.put("/{cid}")
def update_category(cid: int, body: CategoryIn, conn: Connection = Depends(get_db)):
    """改名/换图标；改名需级联更新引用了该大类的食材与冰箱项。"""
    row = conn.execute("SELECT * FROM categories WHERE id=?", (cid,)).fetchone()
    if not row:
        raise HTTPException(404, "大类不存在")
    name = body.name.strip()
    if not name:
        raise HTTPException(422, "名称不能为空")
    if conn.execute("SELECT 1 FROM categories WHERE name=? AND id!=?", (name, cid)).fetchone():
        raise HTTPException(409, "该大类已存在")
    old = row["name"]
    conn.execute(
        "UPDATE categories SET name=?, icon=? WHERE id=?", (name, body.icon or "🥗", cid)
    )
    # 级联改名：把引用旧大类的食材/冰箱项迁移到新大类
    if old != name:
        conn.execute("UPDATE ingredients SET cat=? WHERE cat=?", (name, old))
        conn.execute("UPDATE fridge_items SET cat=? WHERE cat=?", (name, old))
    return {"id": cid, "ok": True}


@router.post("/{cid}/move")
def move_category(cid: int, body: CategoryMove, conn: Connection = Depends(get_db)):
    """上下移动排序：与该方向相邻的大类交换 sort。"""
    row = conn.execute("SELECT * FROM categories WHERE id=?", (cid,)).fetchone()
    if not row:
        raise HTTPException(404, "大类不存在")
    direction = -1 if body.dir == "up" else 1
    # 相邻项：sort 严格大于（down）/小于（up）且最接近的
    cmp = ">" if direction == 1 else "<"
    nxt = conn.execute(
        f"SELECT * FROM categories WHERE sort {cmp} ? ORDER BY sort {'ASC' if direction == 1 else 'DESC'} LIMIT 1",
        (row["sort"],),
    ).fetchone()
    if not nxt:
        return {"id": cid, "ok": True}  # 已在边界，无需移动
    cid, csort, nid, nsort = cid, row["sort"], nxt["id"], nxt["sort"]
    conn.execute("UPDATE categories SET sort=? WHERE id=?", (nsort, cid))
    conn.execute("UPDATE categories SET sort=? WHERE id=?", (csort, nid))
    return {"id": cid, "ok": True}


@router.delete("/{cid}")
def delete_category(cid: int, conn: Connection = Depends(get_db)):
    """删除大类；该大类下的食材/冰箱项退回兜底「其他」。"""
    row = conn.execute("SELECT * FROM categories WHERE id=?", (cid,)).fetchone()
    if not row:
        raise HTTPException(404, "大类不存在")
    name = row["name"]
    _ensure_fallback(conn)
    conn.execute("UPDATE ingredients SET cat=? WHERE cat=?", (FALLBACK_CAT, name))
    conn.execute("UPDATE fridge_items SET cat=? WHERE cat=?", (FALLBACK_CAT, name))
    conn.execute("DELETE FROM categories WHERE id=?", (cid,))
    return {"id": cid, "ok": True}