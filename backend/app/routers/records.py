# -*- coding: utf-8 -*-
"""饮食记录路由：唯一 id，支持编辑/删除；日历按天聚合。

type：cook 自己做 / out 餐厅 / delivery 外卖。
统计（如某类型占比）为派生数据，由前端按需实时计算，后端不落冗余。
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlite3 import Connection

from app.db import get_db, row_to_dict

router = APIRouter(prefix="/records", tags=["records"])


class RecordIn(BaseModel):
    date: str          # YYYY-MM-DD
    name: str
    type: str = "cook" # cook|out|delivery


def _get(conn: Connection, rid: int):
    row = conn.execute("SELECT * FROM records WHERE id=?", (rid,)).fetchone()
    if not row:
        raise HTTPException(404, "记录不存在")
    return row_to_dict(row)


@router.get("")
def list_records(
    start: Optional[str] = None,
    end: Optional[str] = None,
    date: Optional[str] = None,
    conn: Connection = Depends(get_db),
):
    """按日期范围或单日查询饮食记录。"""
    if date:
        rows = conn.execute("SELECT * FROM records WHERE date=? ORDER BY id", (date,)).fetchall()
    elif start and end:
        rows = conn.execute(
            "SELECT * FROM records WHERE date BETWEEN ? AND ? ORDER BY date, id",
            (start, end),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM records ORDER BY date DESC, id").fetchall()
    return [row_to_dict(r) for r in rows]


@router.get("/calendar")
def calendar(conn: Connection = Depends(get_db)):
    """按天聚合：返回 {date: [记录...]}，供日历展示。"""
    rows = conn.execute("SELECT * FROM records ORDER BY date, id").fetchall()
    agg = {}
    for r in rows:
        agg.setdefault(r["date"], []).append(row_to_dict(r))
    return agg


@router.post("")
def create_record(body: RecordIn, conn: Connection = Depends(get_db)):
    cur = conn.execute(
        "INSERT INTO records(date,name,type) VALUES(?,?,?)",
        (body.date, body.name, body.type),
    )
    return {"id": cur.lastrowid, "ok": True}


@router.put("/{rid}")
def update_record(rid: int, body: RecordIn, conn: Connection = Depends(get_db)):
    """编辑记录：改名/改类型/改日期，原地更新。"""
    _get(conn, rid)
    conn.execute(
        "UPDATE records SET date=?, name=?, type=? WHERE id=?",
        (body.date, body.name, body.type, rid),
    )
    return {"id": rid, "ok": True}


@router.delete("/{rid}")
def delete_record(rid: int, conn: Connection = Depends(get_db)):
    _get(conn, rid)
    conn.execute("DELETE FROM records WHERE id=?", (rid,))
    return {"id": rid, "ok": True}