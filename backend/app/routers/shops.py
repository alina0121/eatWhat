# -*- coding: utf-8 -*-
"""餐厅收藏路由：新增/编辑共用同一表单，含到达耗时(arr_min)+交通工具(transport)。"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlite3 import Connection

from app.db import get_db, jdump, jload, row_to_dict
from app.routers.auth import get_optional_user, get_write_user

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
    icon: str = "🏪"


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
    icon: Optional[str] = None


def _get(conn: Connection, sid: int, user: int):
    """取餐厅并校验归属：餐厅收藏按人隔离，只能看/改自己的。"""
    row = conn.execute("SELECT * FROM shops WHERE id=?", (sid,)).fetchone()
    if not row or row["user_id"] != user:
        raise HTTPException(404, "餐厅不存在")
    return row_to_dict(row)


@router.get("")
def list_shops(user: int = Depends(get_optional_user),
               conn: Connection = Depends(get_db)):
    """当前用户收藏的餐厅。未登录（user=0）为空。"""
    rows = conn.execute(
        "SELECT * FROM shops WHERE user_id=? ORDER BY star DESC", (user,)
    ).fetchall()
    return [row_to_dict(r) for r in rows]


@router.post("")
def create_shop(body: ShopIn,
                user: int = Depends(get_write_user),
                conn: Connection = Depends(get_db)):
    cur = conn.execute(
        "INSERT INTO shops(user_id,name,type,price,star,must,note,arr_min,transport,tags,icon) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (user, body.name, body.type, body.price, body.star, jdump(body.must),
         body.note, body.arr_min, body.transport, jdump(body.tags), body.icon or '🏪'),
    )
    return {"id": cur.lastrowid, "ok": True}


@router.get("/{sid}")
def get_shop(sid: int,
             user: int = Depends(get_optional_user),
             conn: Connection = Depends(get_db)):
    return _get(conn, sid, user)


@router.put("/{sid}")
def update_shop(sid: int, body: ShopPatch,
                user: int = Depends(get_write_user),
                conn: Connection = Depends(get_db)):
    _get(conn, sid, user)  # 校验存在且属于当前用户
    data = body.model_dump(exclude_none=True)
    if "must" in data:
        data["must"] = jdump(data["must"])
    if "tags" in data:
        data["tags"] = jdump(data["tags"])
    sets = ", ".join(f"{k}=?" for k in data)
    conn.execute(f"UPDATE shops SET {sets} WHERE id=?", (*data.values(), sid))
    return {"id": sid, "ok": True}


@router.delete("/{sid}")
def delete_shop(sid: int,
                user: int = Depends(get_write_user),
                conn: Connection = Depends(get_db)):
    _get(conn, sid, user)
    conn.execute("DELETE FROM shops WHERE id=?", (sid,))
    # 连带清理该用户自己的「吃这些」里的这家店候选（别人的候选不动）
    conn.execute(
        "DELETE FROM eat_inbox WHERE kind='shop' AND ref_id=? AND user_id=?",
        (sid, user),
    )
    return {"id": sid, "ok": True}