# -*- coding: utf-8 -*-
"""
冰箱路由：按 user_id 隔离，每个用户维护自己的冰箱与待采购。

- 在库单条含「采购日期 + 保质期天数」，状态实时现算，不落库。
- 待采购既可由候选代号入（见 candidates），也可手工维护。
"""
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlite3 import Connection

from app.db import get_db, jdump, row_to_dict
from .auth import get_optional_user
from app.routers.configs import get_config

router = APIRouter(prefix="/fridge", tags=["fridge"])


class InStockIn(BaseModel):
    name: str
    cat: str = "其他"
    qty: float = 1
    unit: str = "份"
    store: str = ""
    buy: str = ""          # YYYY-MM-DD，空则取今天
    days: int = 7          # 保质期（天）


class PurchaseIn(BaseModel):
    name: str
    qty: float = 1
    unit: str = "份"


def _merge_in_stock(conn: Connection, user_id: int):
    """按 (name, unit) 汇总**某用户**在库总量，供候选代号入比对用。"""
    rows = conn.execute(
        "SELECT name, unit, SUM(qty) AS total FROM fridge_items "
        "WHERE user_id=? GROUP BY name, unit", (user_id,)
    ).fetchall()
    return {(r["name"], r["unit"]): r["total"] for r in rows}


def _compute_line(r: dict, threshold_days: int, today: date) -> dict:
    """为单条在库计算状态/剩余天数（实时派生）。"""
    status = "充足"
    remain = None
    buy = (r.get("buy") or "").strip()
    if buy:
        try:
            bd = date.fromisoformat(buy)
        except ValueError:
            return {**r, "status": status, "remain": remain}
        remain = r["days"] + (bd - today).days
        if remain < 0:
            status = "已过期"
        elif remain <= threshold_days:
            status = "临期"
    return {**r, "status": status, "remain": remain}


# ── 在库 ─────────────────────────────────────────────────────────────────

@router.get("/in_stock")
def list_in_stock(user: int = Depends(get_optional_user), conn: Connection = Depends(get_db)):
    today = date.today()
    threshold = int(get_config(conn, "expiry_threshold_days", "3"))
    rows = conn.execute(
        "SELECT * FROM fridge_items WHERE user_id=? ORDER BY id", (user,)
    ).fetchall()
    return [_compute_line(row_to_dict(r), threshold, today) for r in rows]


@router.post("/in_stock")
def add_in_stock(body: InStockIn, user: int = Depends(get_optional_user), conn: Connection = Depends(get_db)):
    buy = body.buy or date.today().isoformat()
    cur = conn.execute(
        "INSERT INTO fridge_items(user_id,name,cat,qty,unit,store,buy,days) "
        "VALUES(?,?,?,?,?,?,?,?)",
        (user, body.name, body.cat, body.qty, body.unit, body.store, buy, body.days),
    )
    return {"id": cur.lastrowid, "ok": True}


@router.put("/in_stock/{fid}")
def update_in_stock(fid: int, body: InStockIn, user: int = Depends(get_optional_user), conn: Connection = Depends(get_db)):
    row = conn.execute("SELECT * FROM fridge_items WHERE id=?", (fid,)).fetchone()
    if not row:
        raise HTTPException(404, "食材不存在")
    if row["user_id"] != user:
        raise HTTPException(403, "无权修改他人冰箱")
    buy = body.buy or row["buy"] or date.today().isoformat()
    conn.execute(
        "UPDATE fridge_items SET name=?,cat=?,qty=?,unit=?,store=?,buy=?,days=? WHERE id=?",
        (body.name, body.cat, body.qty, body.unit, body.store, buy, body.days, fid),
    )
    return {"id": fid, "ok": True}


@router.delete("/in_stock/{fid}")
def delete_in_stock(fid: int, user: int = Depends(get_optional_user), conn: Connection = Depends(get_db)):
    conn.execute("DELETE FROM fridge_items WHERE id=? AND user_id=?", (fid, user))
    return {"id": fid, "ok": True}


# ── 待采购 ─────────────────────────────────────────────────────────────────

@router.get("/purchase")
def list_purchase(user: int = Depends(get_optional_user), conn: Connection = Depends(get_db)):
    rows = conn.execute(
        "SELECT * FROM purchase WHERE user_id=? ORDER BY id", (user,)
    ).fetchall()
    return [row_to_dict(r) for r in rows]


def _purchase_upsert(conn: Connection, user_id: int, name: str, unit: str, qty: float) -> int:
    """待采购行 upsert：同用户同名同单位累加数量。"""
    row = conn.execute(
        "SELECT id FROM purchase WHERE user_id=? AND name=? AND unit=?",
        (user_id, name, unit),
    ).fetchone()
    if row:
        conn.execute("UPDATE purchase SET qty=qty+? WHERE id=?", (qty, row["id"]))
        return row["id"]
    cur = conn.execute(
        "INSERT INTO purchase(user_id,name,qty,unit) VALUES(?,?,?,?)",
        (user_id, name, qty, unit),
    )
    return cur.lastrowid


@router.post("/purchase")
def add_purchase(body: PurchaseIn, user: int = Depends(get_optional_user), conn: Connection = Depends(get_db)):
    """手工新增；同用户同名同单位则累加。"""
    _purchase_upsert(conn, user, body.name, body.unit, body.qty)
    return {"ok": True}


@router.delete("/purchase/{pid}")
def delete_purchase(pid: int, user: int = Depends(get_optional_user), conn: Connection = Depends(get_db)):
    conn.execute("DELETE FROM purchase WHERE id=? AND user_id=?", (pid, user))
    return {"id": pid, "ok": True}


@router.put("/purchase/{pid}")
def update_purchase(pid: int, body: PurchaseIn, user: int = Depends(get_optional_user), conn: Connection = Depends(get_db)):
    """编辑待采购；改名后若 (user_id, name, unit) 已存在则账量合并。"""
    row = conn.execute(
        "SELECT * FROM purchase WHERE id=? AND user_id=?", (pid, user)
    ).fetchone()
    if not row:
        raise HTTPException(404, "待采购不存在")
    name, unit = body.name.strip(), body.unit or "份"
    other = conn.execute(
        "SELECT id FROM purchase WHERE user_id=? AND name=? AND unit=? AND id!=?",
        (user, name, unit, pid),
    ).fetchone()
    if other:
        conn.execute("UPDATE purchase SET qty=qty+? WHERE id=?", (body.qty, other["id"]))
        conn.execute("DELETE FROM purchase WHERE id=?", (pid,))
    else:
        conn.execute(
            "UPDATE purchase SET name=?,qty=?,unit=? WHERE id=?", (name, body.qty, unit, pid)
        )
    return {"ok": True}


@router.post("/purchase/{pid}/to-stock")
def purchase_to_stock(pid: int, user: int = Depends(get_optional_user), conn: Connection = Depends(get_db)):
    """「已采购」：待采购转入**同用户**在库，删除待采购行。"""
    row = conn.execute(
        "SELECT * FROM purchase WHERE id=? AND user_id=?", (pid, user)
    ).fetchone()
    if not row:
        raise HTTPException(404, "待采购不存在")
    ing = conn.execute(
        "SELECT cat FROM ingredients WHERE user_id=? AND name=?", (user, row["name"])
    ).fetchone()
    cat = ing["cat"] if ing else "其他"
    conn.execute(
        "INSERT INTO fridge_items(user_id,name,cat,qty,unit,store,buy,days) "
        "VALUES(?,?,?,?,?,?,?,?)",
        (user, row["name"], cat, row["qty"], row["unit"], "",
         date.today().isoformat(), 7),
    )
    conn.execute("DELETE FROM purchase WHERE id=? AND user_id=?", (pid, user))
    return {"ok": True}
