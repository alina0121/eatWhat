# -*- coding: utf-8 -*-
"""
食材库路由：菜谱选食材的独立维护来源（与冰箱库存解耦）。

设计：菜谱的「所需食材」是需求，不从库存（在库/待采购）派生；用户在食材库
单独维护一套可选项（含大类），菜谱编辑时两级下拉（大类 → 食材名）从这里取。
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlite3 import Connection

from app.db import get_db, row_to_dict

router = APIRouter(prefix="/ingredients", tags=["ingredients"])


class IngredientIn(BaseModel):
    name: str
    cat: str = "其他"


@router.get("")
def list_ingredients(conn: Connection = Depends(get_db)):
    """食材库清单（按大类 + 名称排序，便于前端分组）。"""
    rows = conn.execute(
        "SELECT * FROM ingredients ORDER BY cat, name"
    ).fetchall()
    return [row_to_dict(r) for r in rows]


@router.post("")
def create_ingredient(body: IngredientIn, conn: Connection = Depends(get_db)):
    """新增食材到食材库；同名去重。"""
    name = body.name.strip()
    if not name:
        raise HTTPException(422, "名称不能为空")
    dup = conn.execute("SELECT 1 FROM ingredients WHERE name=?", (name,)).fetchone()
    if dup:
        raise HTTPException(409, "该食材已在食材库")
    cur = conn.execute(
        "INSERT INTO ingredients(name,cat) VALUES(?,?)", (name, body.cat)
    )
    return {"id": cur.lastrowid, "ok": True}


@router.put("/{iid}")
def update_ingredient(iid: int, body: IngredientIn, conn: Connection = Depends(get_db)):
    """编辑食材库条目（改名/改大类）。改名冲突则 409。"""
    name = body.name.strip()
    if not conn.execute("SELECT 1 FROM ingredients WHERE id=?", (iid,)).fetchone():
        raise HTTPException(404, "食材不存在")
    if conn.execute("SELECT 1 FROM ingredients WHERE name=? AND id!=?", (name, iid)).fetchone():
        raise HTTPException(409, "该食材已在食材库")
    conn.execute(
        "UPDATE ingredients SET name=?, cat=? WHERE id=?", (name, body.cat, iid)
    )
    return {"id": iid, "ok": True}


@router.delete("/{iid}")
def delete_ingredient(iid: int, conn: Connection = Depends(get_db)):
    """从食材库移除（不影响已用该食材的菜谱/库存，只是不再可选）。"""
    conn.execute("DELETE FROM ingredients WHERE id=?", (iid,))
    return {"id": iid, "ok": True}