# -*- coding: utf-8 -*-
"""
候选收件箱「吃这些」路由（核心业务，含 COOK 一致性保证）。

关键交互（对齐第一版 UI 基准）：
1. 加入候选：某道菜谱进入「吃这些」时，逐食材与冰箱在库比对，缺的自动代入待采购（带数量）。
2. 移除候选：把代入的待采购量**按量回退**（扣除，非清零），保证加几次扣几次、不多不少。
3. 餐厅候选：只进候选，不参与采购计算（代入/回退 dose nothing）。
4. COOK 一致性：加入 → 代入，移除 → 回退，全在**同一个数据库事务**内完成，要么全成要么全不成。
5. 空间：space=mine 个人池（默认）/ space=family 家庭共享池（families.py 建家庭、成员凭邀请码加入）。
   家庭池内成员人人可见、可加/删/启停计时；缺货代入与回退始终记在**加者**的 fridge/purchase 上。
   老数据 creator_id=0，回退用 user_id（历史候选本来 user_id 就是加它的人）。

实现细节：
- 候选记录美食材代入的映射 subs={name+unit: 数量}，移除时据此精确回退待采购。
- 计时 tracks 挂载在候选上，一个候选一个计时（可多道并行）：
  运行中 elapsed = 已暂停秒 + (now - started)；暂停中只算已暂停秒。
"""
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlite3 import Connection

from app.db import get_db, jdump, jload, row_to_dict
from .auth import get_optional_user, get_write_user

router = APIRouter(prefix="/candidates", tags=["candidates"])


class CandidateIn(BaseModel):
    kind: str          # recipe | shop
    ref_id: int        # 关联菜谱/餐厅 id
    space: str = "mine"  # mine 个人池 | family 家庭空间共享池


def _member_family_id(conn: Connection, uid: int):
    """该用户所在家庭 id；未加入家庭返回 None。"""
    row = conn.execute(
        "SELECT f.id FROM families f JOIN family_members m ON m.family_id=f.id WHERE m.user_id=?",
        (uid,),
    ).fetchone()
    return row["id"] if row else None


def _ingest_subs(conn: Connection, ref_id: int, user_id: int) -> str:
    """根据菜谱食材与**某用户**冰箱比对，计算缺货代入的待采购映射（JSON 字符串）。

    待采购也按 user_id 隔离，用 Python upsert（不依赖 SQLite ON CONFLICT 约束）。
    """
    rec = conn.execute("SELECT ing FROM recipes WHERE id=?", (ref_id,)).fetchone()
    if not rec:
        return "{}"
    ing = jload(rec["ing"])

    # 该用户的在库总量
    in_stock = {}
    for r in conn.execute(
        "SELECT name, unit, SUM(qty) AS total FROM fridge_items "
        "WHERE user_id=? GROUP BY name, unit", (user_id,)
    ).fetchall():
        in_stock[(r["name"], r["unit"])] = r["total"]

    subs = {}
    for it in ing:
        name, unit = it.get("name", ""), it.get("unit", "份")
        need = it.get("qty", 1)
        have = in_stock.get((name, unit), 0.0)
        deficit = max(0.0, need - have)
        if deficit <= 0:
            continue
        # 待采购 upsert（同用户同名同单位累加）
        row = conn.execute(
            "SELECT id FROM purchase WHERE user_id=? AND name=? AND unit=?",
            (user_id, name, unit),
        ).fetchone()
        if row:
            conn.execute("UPDATE purchase SET qty=qty+? WHERE id=?", (deficit, row["id"]))
        else:
            conn.execute(
                "INSERT INTO purchase(user_id,name,qty,unit) VALUES(?,?,?,?)",
                (user_id, name, deficit, unit),
            )
        key = f"{name}\x00{unit}"
        subs[key] = subs.get(key, 0.0) + deficit

    return jdump(subs)


def _subtract_subs(conn: Connection, subs: dict, user_id: int):
    """按量回退**某用户**的待采购。"""
    for key, qty in subs.items():
        name, unit = key.split("\x00", 1)
        row = conn.execute(
            "SELECT id, qty FROM purchase WHERE user_id=? AND name=? AND unit=?",
            (user_id, name, unit),
        ).fetchone()
        if not row:
            continue
        remain = row["qty"] - qty
        if remain <= 0:
            conn.execute("DELETE FROM purchase WHERE id=?", (row["id"],))
        else:
            conn.execute("UPDATE purchase SET qty=? WHERE id=?", (remain, row["id"]))


def _enrich_track(cand: dict, conn: Connection) -> dict:
    """给候选附上计时状态：elapsed 秒（实时现算）、running 标记。"""
    tr = conn.execute("SELECT * FROM tracks WHERE inbox_id=?", (cand["id"],)).fetchone()
    if tr is None:
        return {**cand, "timer": None}
    running, paused, started = tr["running"], tr["paused"], tr["started"]
    if running and started:
        start = datetime.fromisoformat(started)
        elapsed = paused + (datetime.now() - start).total_seconds()
    else:
        elapsed = paused
    return {**cand, "timer": {"running": bool(running), "elapsed": round(elapsed)}}


def _get_owned_inbox(conn: Connection, cid: int, user: int) -> dict:
    """取候选并校验操作权：个人池只能操作自己的；家庭池内任何成员都可操作。"""
    row = conn.execute("SELECT * FROM eat_inbox WHERE id=?", (cid,)).fetchone()
    if not row:
        raise HTTPException(404, "候选不存在")
    if row["family_id"]:
        if row["family_id"] != (_member_family_id(conn, user) or -1):
            raise HTTPException(404, "候选不存在")
    elif row["user_id"] != user:
        raise HTTPException(404, "候选不存在")
    return row_to_dict(row)


def _creator_uid(row: dict) -> int:
    """该候选的加者（记账对象）：缺货代入/回退都落在加者的待采购上。

    老数据 creator_id=0，回退用 user_id（两者语义一致：候选属于加它的人）。
    """
    return row.get("creator_id") or row.get("user_id") or 0


@router.get("")
def list_candidates(space: str = "mine",
                    user: int = Depends(get_optional_user),
                    conn: Connection = Depends(get_db)):
    """返回候选列表，附带实时计时状态。未登录（user=0）为空。

    - space=mine（默认）：个人池（family_id=0 且是自己的候选）。
    - space=family：所在家庭空间的共享池（成员可见、可加/删/启停计时）。
    """
    if space == "family":
        fid = _member_family_id(conn, user)
        if not fid:
            return []
        rows = conn.execute(
            "SELECT * FROM eat_inbox WHERE family_id=? ORDER BY id", (fid,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM eat_inbox WHERE user_id=? AND family_id=0 ORDER BY id", (user,)
        ).fetchall()
    out = []
    for r in rows:
        d = row_to_dict(r)
        # 餐厅候选的图标实时跟随餐厅编辑（兼容加入时被硬编码为默认图标的存量记录）
        if d.get("kind") == "shop":
            sh = conn.execute("SELECT icon FROM shops WHERE id=?", (d["ref_id"],)).fetchone()
            if sh and sh["icon"]:
                d["em"] = sh["icon"]
        out.append(_enrich_track(d, conn))
    return out


@router.post("")
def add_candidate(body: CandidateIn,
                  user: int = Depends(get_write_user),
                  conn: Connection = Depends(get_db)):
    """加入候选。整个方法在一个事务里（get_db 提交/回滚）：

    - kind=recipe：取菜谱名/表情，计算**加者**的缺货代入待采购并记录 subs。
      家庭空间加菜时，缺货照样代入**加者自己**的待采购（回退也回他的）。
    - kind=shop ：仅入候选，不参与采购。
    - space=family：进家庭共享池，全体成员可见可操作；查重按空间维度。
    """
    kind = body.kind
    ref_id = body.ref_id
    fid = 0
    if body.space == "family":
        fid = _member_family_id(conn, user) or 0
        if not fid:
            raise HTTPException(400, "还没加入家庭空间，先到「我的-家庭」创建或加入")
    subs = "{}"
    if kind == "recipe":
        rec = conn.execute("SELECT name, em FROM recipes WHERE id=?", (ref_id,)).fetchone()
        if not rec:
            raise HTTPException(404, "菜谱不存在")
        name, em = rec["name"], rec["em"]
        subs = _ingest_subs(conn, ref_id, user)
    elif kind == "shop":
        sh = conn.execute("SELECT name, icon FROM shops WHERE id=?", (ref_id,)).fetchone()
        if not sh:
            raise HTTPException(404, "餐厅不存在")
        # 图标跟随餐厅编辑设置（此前硬编码 🏪，导致候选列表显示默认图标）
        name, em = sh["name"], sh["icon"] or "🏪"
    else:
        raise HTTPException(400, "kind 须为 recipe 或 shop")

    # 查重按空间维度：家庭池同空间内不能重复；个人池只查自己的
    if fid:
        dup = conn.execute(
            "SELECT id FROM eat_inbox WHERE kind=? AND ref_id=? AND family_id=?",
            (kind, ref_id, fid),
        ).fetchone()
    else:
        dup = conn.execute(
            "SELECT id FROM eat_inbox WHERE kind=? AND ref_id=? AND user_id=? AND family_id=0",
            (kind, ref_id, user),
        ).fetchone()
    if dup:
        raise HTTPException(400, "该候选已在「吃这些」里")

    cur = conn.execute(
        "INSERT INTO eat_inbox(user_id,kind,ref_id,name,em,subs,family_id,creator_id) "
        "VALUES(?,?,?,?,?,?,?,?)",
        (user, kind, ref_id, name, em, subs, fid, user),
    )
    return {"id": cur.lastrowid, "ok": True}


@router.delete("/{cid}")
def remove_candidate(cid: int,
                     user: int = Depends(get_write_user),
                     conn: Connection = Depends(get_db)):
    """移除候选：按量回退**加者**代入的待采购（餐厅无代入则无影响），同事务保证一致。

    家庭池里 B 删 A 加的候选 → 回退 A 的待采购（谁加的记谁的账）。
    """
    row = _get_owned_inbox(conn, cid, user)
    # _get_owned_inbox 走 row_to_dict，subs 已是 dict（JSON 自动反序列化）；兜底容错一次
    subs = row["subs"] if isinstance(row["subs"], dict) else jload(row["subs"], default={})
    _subtract_subs(conn, subs, _creator_uid(row))
    conn.execute("DELETE FROM tracks WHERE inbox_id=?", (cid,))
    conn.execute("DELETE FROM eat_inbox WHERE id=?", (cid,))
    return {"id": cid, "ok": True}


# ---------------------------------------------------------------------------
# 计时（多道并行：一个候选一个计时，互不影响）
# ---------------------------------------------------------------------------
@router.post("/{cid}/timer/start")
def timer_start(cid: int,
                user: int = Depends(get_write_user),
                conn: Connection = Depends(get_db)):
    """开始/继续计时。

    - 从未计时：新建一条跑表 started=now。
    - 已暂停：继续（保留已累计的 paused 秒），不归零。
    - 已运行：幂等，直接返回当前状态。
    """
    _get_owned_inbox(conn, cid, user)
    tr = conn.execute("SELECT * FROM tracks WHERE inbox_id=?", (cid,)).fetchone()
    if tr and tr["running"]:
        return {"cid": cid, "running": True, "ok": True}
    if tr:
        # 恢复暂停：保留 paused，重新走表
        conn.execute(
            "UPDATE tracks SET running=1, started=? WHERE id=?",
            (datetime.now().isoformat(), tr["id"]),
        )
    else:
        conn.execute(
            "INSERT INTO tracks(inbox_id,started,paused,running) VALUES(?,?,0,1)",
            (cid, datetime.now().isoformat()),
        )
    return {"cid": cid, "running": True, "ok": True}


@router.post("/{cid}/timer/pause")
def timer_pause(cid: int,
                user: int = Depends(get_write_user),
                conn: Connection = Depends(get_db)):
    """暂停计时：把累计运行时间并入 paused，停止走表。"""
    _get_owned_inbox(conn, cid, user)
    tr = conn.execute("SELECT * FROM tracks WHERE inbox_id=?", (cid,)).fetchone()
    if not tr or not tr["running"]:
        raise HTTPException(400, "计时未在运行")
    start = datetime.fromisoformat(tr["started"])
    paused = tr["paused"] + (datetime.now() - start).total_seconds()
    conn.execute(
        "UPDATE tracks SET paused=?, running=0, started=NULL WHERE id=?",
        (paused, tr["id"]),
    )
    return {"cid": cid, "running": False, "ok": True}


@router.post("/{cid}/timer/cancel")
def timer_cancel(cid: int,
                 user: int = Depends(get_write_user),
                 conn: Connection = Depends(get_db)):
    """取消计时：删除计时记录，候选仍保留在吃这些。"""
    _get_owned_inbox(conn, cid, user)
    conn.execute("DELETE FROM tracks WHERE inbox_id=?", (cid,))
    return {"cid": cid, "ok": True}


@router.get("/{cid}/timer")
def timer_get(cid: int,
              user: int = Depends(get_optional_user),
              conn: Connection = Depends(get_db)):
    """查询某个候选的实时计时状态。"""
    cand = _get_owned_inbox(conn, cid, user)
    return _enrich_track(cand, conn)["timer"]
