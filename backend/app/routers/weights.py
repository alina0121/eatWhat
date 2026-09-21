# -*- coding: utf-8 -*-
"""体重记录路由（含体脂）。体脂曲线等派生数据由前端实时计算，后端只存原始体重/体脂。"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlite3 import Connection

from app.db import get_db, row_to_dict

router = APIRouter(prefix="/weights", tags=["weights"])


class WeightIn(BaseModel):
    date: str
    weight: float
    body_fat: Optional[float] = None


def _get(conn: Connection, wid: int):
    row = conn.execute("SELECT * FROM weights WHERE id=?", (wid,)).fetchone()
    if not row:
        raise HTTPException(404, "记录不存在")
    return row_to_dict(row)


@router.get("")
def list_weights(conn: Connection = Depends(get_db)):
    rows = conn.execute("SELECT * FROM weights ORDER BY date").fetchall()
    return [row_to_dict(r) for r in rows]


@router.post("")
def create_weight(body: WeightIn, conn: Connection = Depends(get_db)):
    cur = conn.execute(
        "INSERT INTO weights(date,weight,body_fat) VALUES(?,?,?)",
        (body.date, body.weight, body.body_fat),
    )
    return {"id": cur.lastrowid, "ok": True}


@router.put("/{wid}")
def update_weight(wid: int, body: WeightIn, conn: Connection = Depends(get_db)):
    _get(conn, wid)
    conn.execute(
        "UPDATE weights SET date=?, weight=?, body_fat=? WHERE id=?",
        (body.date, body.weight, body.body_fat, wid),
    )
    return {"id": wid, "ok": True}


@router.delete("/{wid}")
def delete_weight(wid: int, conn: Connection = Depends(get_db)):
    conn.execute("DELETE FROM weights WHERE id=?", (wid,))
    return {"id": wid, "ok": True}