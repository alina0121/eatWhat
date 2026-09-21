# -*- coding: utf-8 -*-
"""
冰箱路由：在库（fridge_items）+ 待采购（purchase）。

- 在库单条含「采购日期 + 保质期天数」，状态（充足/临期/已过期）实时现算，不落库。
  临期判定：今天 - 采购日期 >= 保质期 - 阈值天数 即视作临期。
- 待采购既可由候选代号入（见 candidates 单事务），也可手工维护。
"""
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlite3 import Connection

from app.db import get_db, jdump, row_to_dict
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


def _merge_in_stock(conn: Connection):
    """按 (name, unit) 汇总在库总量，供候选代号入比对用。"""
    rows = conn.execute(
        "SELECT name, unit, SUM(qty) AS total FROM fridge_items "
        "GROUP BY name, unit"
    ).fetchall()
    return {(r["name"], r["unit"]): r["total"] for r in rows}


def _compute_line(r: dict, threshold_days: int, today: date) -> dict:
    """为单条在库计算状态/剩余天数（实时派生，out 字段）。"""
    status = "充足"
    remain = None
    if r.get("buy"):
        bd = date.fromisoformat(r["buy"])
        remain = r["days"] + (bd - today).days  # 剩余可用天数
        if remain < 0:
            status = "已过期"
        elif remain <= threshold_days:
            status = "临期"
    return {**r, "status": status, "remain": remain}


@router.get("/in_stock")
def list_in_stock(conn: Connection = Depends(get_db)):
    """返回在库清单，每条附带实时计算的 status/remain。"""
    today = date.today()
    threshold = int(get_config(conn, "expiry_threshold_days", "3"))
    rows = conn.execute("SELECT * FROM fridge_items ORDER BY id").fetchall()
    return [_compute_line(row_to_dict(r), threshold, today) for r in rows]


@router.post("/in_stock")
def add_in_stock(body: InStockIn, conn: Connection = Depends(get_db)):
    """新增在库食材；buy 留空则记为今天。"""
    buy = body.buy or date.today().isoformat()
    cur = conn.execute(
        "INSERT INTO fridge_items(name,cat,qty,unit,store,buy,days) VALUES(?,?,?,?,?,?,?)",
        (body.name, body.cat, body.qty, body.unit, body.store, buy, body.days),
    )
    return {"id": cur.lastrowid, "ok": True}


@router.put("/in_stock/{fid}")
def update_in_stock(fid: int, body: InStockIn, conn: Connection = Depends(get_db)):
    """编辑在库食材（复用新增表单回填）。"""
    buy = body.buy or date.today().isoformat()
    cur = conn.execute(
        "UPDATE fridge_items SET name=?,cat=?,qty=?,unit=?,store=?,buy=?,days=? WHERE id=?",
        (body.name, body.cat, body.qty, body.unit, body.store, buy, body.days, fid),
    )
    if cur.rowcount == 0:
        raise HTTPException(404, "食材不存在")
    return {"id": fid, "ok": True}


@router.delete("/in_stock/{fid}")
def delete_in_stock(fid: int, conn: Connection = Depends(get_db)):
    conn.execute("DELETE FROM fridge_items WHERE id=?", (fid,))
    return {"id": fid, "ok": True}


@router.get("/purchase")
def list_purchase(conn: Connection = Depends(get_db)):
    """待采购清单。"""
    rows = conn.execute("SELECT * FROM purchase ORDER BY id").fetchall()
    return [row_to_dict(r) for r in rows]


@router.post("/purchase")
def add_purchase(body: PurchaseIn, conn: Connection = Depends(get_db)):
    """手工新增待采购；同名同单位则累加数量。"""
    conn.execute(
        "INSERT INTO purchase(name,qty,unit) VALUES(?,?,?) "
        "ON CONFLICT(name,unit) DO UPDATE SET qty=qty+excluded.qty",
        (body.name, body.qty, body.unit),
    )
    return {"ok": True}


@router.delete("/purchase/{pid}")
def delete_purchase(pid: int, conn: Connection = Depends(get_db)):
    conn.execute("DELETE FROM purchase WHERE id=?", (pid,))
    return {"id": pid, "ok": True}


@router.put("/purchase/{pid}")
def update_purchase(pid: int, body: PurchaseIn, conn: Connection = Depends(get_db)):
    """编辑待采购（改名/改量）。若新 (name,unit) 已存在则账量合并到该行，删掉本行。"""
    row = conn.execute("SELECT * FROM purchase WHERE id=?", (pid,)).fetchone()
    if not row:
        raise HTTPException(404, "待采购不存在")
    name, unit = body.name.strip(), body.unit or "份"
    other = conn.execute(
        "SELECT id FROM purchase WHERE name=? AND unit=? AND id!=?", (name, unit, pid)
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
def purchase_to_stock(pid: int, conn: Connection = Depends(get_db)):
    """「已采购」：把待采购转入在库（采购日期=今天），并删除待采购行。

    大类优先取食材库登记的大类；未登记则归「其他」。同事务完成，保持一致。
    """
    row = conn.execute("SELECT * FROM purchase WHERE id=?", (pid,)).fetchone()
    if not row:
        raise HTTPException(404, "待采购不存在")
    ing = conn.execute("SELECT cat FROM ingredients WHERE name=?", (row["name"],)).fetchone()
    cat = ing["cat"] if ing else "其他"
    conn.execute(
        "INSERT INTO fridge_items(name,cat,qty,unit,store,buy,days) VALUES(?,?,?,?,?,?,?)",
        (row["name"], cat, row["qty"], row["unit"], "", date.today().isoformat(), 7),
    )
    conn.execute("DELETE FROM purchase WHERE id=?", (pid,))
    return {"ok": True}