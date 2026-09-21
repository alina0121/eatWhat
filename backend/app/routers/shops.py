# -*- coding: utf-8 -*-
"""餐厅收藏路由：新增/编辑共用同一表单，含到达耗时(arr_min)+交通工具(transport)。"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlite3 import Connection

from app.db import get_db, jdump, jload, row_to_dict

router = APIRouter(prefix="/shops", tags=["shops"])


class ShopIn(BaseModel):
    name: str
    type: str = "中餐"
    price: str = ""
    star: float = 0
    must: List[str] = []      # 招牌菜
    note: str = ""
    arr_min: int = 0
    transport: str = "步行"
    tags: List[str] = []      # 口味标签


class ShopPatch(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    price: Optional[str] = None
    star: Optional[float] = None
    must: Optional[List[str]] = None
    note: Optional[str] = None
    arr_min: Optional[int] = None
    transport: Optional[str] = None
    tags: Optional[List[str]] = None


def _get(conn: Connection, sid: int):
    row = conn.execute("SELECT * FROM shops WHERE id=?", (sid,)).fetchone()
    if not row:
        raise HTTPException(404, "餐厅不存在")
    return row_to_dict(row)


@router.get("")
def list_shops(conn: Connection = Depends(get_db)):
    rows = conn.execute("SELECT * FROM shops ORDER BY star DESC").fetchall()
    return [row_to_dict(r) for r in rows]


@router.post("")
def create_shop(body: ShopIn, conn: Connection = Depends(get_db)):
    cur = conn.execute(
        "INSERT INTO shops(name,type,price,star,must,note,arr_min,transport,tags) "
        "VALUES(?,?,?,?,?,?,?,?,?)",
        (body.name, body.type, body.price, body.star, jdump(body.must),
         body.note, body.arr_min, body.transport, jdump(body.tags)),
    )
    return {"id": cur.lastrowid, "ok": True}


@router.get("/{sid}")
def get_shop(sid: int, conn: Connection = Depends(get_db)):
    return _get(conn, sid)


@router.put("/{sid}")
def update_shop(sid: int, body: ShopPatch, conn: Connection = Depends(get_db)):
    _get(conn, sid)  # 校验存在
    data = body.model_dump(exclude_none=True)
    if "must" in data:
        data["must"] = jdump(data["must"])
    if "tags" in data:
        data["tags"] = jdump(data["tags"])
    sets = ", ".join(f"{k}=?" for k in data)
    conn.execute(f"UPDATE shops SET {sets} WHERE id=?", (*data.values(), sid))
    return {"id": sid, "ok": True}


@router.delete("/{sid}")
def delete_shop(sid: int, conn: Connection = Depends(get_db)):
    conn.execute("DELETE FROM shops WHERE id=?", (sid,))
    conn.execute("DELETE FROM eat_inbox WHERE kind='shop' AND ref_id=?", (sid,))
    return {"id": sid, "ok": True}