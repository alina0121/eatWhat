# -*- coding: utf-8 -*-
"""
菜谱路由。

- source=my   我的菜谱：可新建 / 编辑 / 删除。
- source=admin 参考菜谱：管理员录入、只读（前端可「加入吃这些」或「存进我的菜谱」）。
- 结构化字段（tags/ing/steps）以 JSON 传输，入库序列化为 TEXT。

ing 元素结构：{name, qty, unit}  —— 食材名、用量、单位。
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlite3 import Connection

from app.db import get_db, jdump, jload, row_to_dict
from app.routers.candidates import _subtract_subs

router = APIRouter(prefix="/recipes", tags=["recipes"])


class Ing(BaseModel):
    name: str
    qty: float = 1
    unit: str = "份"


class RecipeIn(BaseModel):
    source: str = "my"        # my | admin
    name: str
    em: str = "🍽"
    cover: str = ""
    time: int = 0
    diff: str = "简单"
    tags: List[str] = []
    ing: List[Ing] = []
    steps: List[str] = []


class RecipePatch(BaseModel):
    name: Optional[str] = None
    em: Optional[str] = None
    cover: Optional[str] = None
    time: Optional[int] = None
    diff: Optional[str] = None
    tags: Optional[List[str]] = None
    ing: Optional[List[Ing]] = None
    steps: Optional[List[str]] = None


def _get(conn: Connection, rid: int):
    row = conn.execute("SELECT * FROM recipes WHERE id=?", (rid,)).fetchone()
    if not row:
        raise HTTPException(404, "菜谱不存在")
    return _enrich_cover(conn, row_to_dict(row))


def _enrich_cover(conn: Connection, d: dict) -> dict:
    """给菜谱附上所选封面的渐变（用于渲染背景）；没选封面时 coverGrad 为空走默认轮换。"""
    cid = d.get("cover")
    if cid:
        cv = conn.execute("SELECT grad FROM covers WHERE id=?", (cid,)).fetchone()
        d["coverGrad"] = cv["grad"] if cv else ""
    return d


@router.get("")
def list_recipes(source: Optional[str] = None, conn: Connection = Depends(get_db)):
    """按来源筛选菜谱；缺省返回全部。"""
    if source:
        rows = conn.execute(
            "SELECT * FROM recipes WHERE source=? ORDER BY id DESC", (source,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM recipes ORDER BY id DESC").fetchall()
    return [_enrich_cover(conn, row_to_dict(r)) for r in rows]


def _check_name_unique(conn: Connection, name: str, exclude_id: Optional[int] = None):
    """我的菜谱不允许同名。参考菜谱不受限。返回冲突菜谱 id 或 None。"""
    row = conn.execute(
        "SELECT id FROM recipes WHERE source='my' AND name=? AND id IS NOT ?",
        (name, exclude_id or -1),
    ).fetchone()
    return row["id"] if row else None


@router.post("")
def create_recipe(body: RecipeIn, conn: Connection = Depends(get_db)):
    """新建菜谱（默认我的菜谱；写 source=admin 即录入参考菜谱）。"""
    if body.source == "my" and _check_name_unique(conn, body.name):
        raise HTTPException(409, "我的菜谱已存在同名，请换个菜名")
    cur = conn.execute(
        "INSERT INTO recipes(source,name,em,cover,time,diff,tags,ing,steps) "
        "VALUES(?,?,?,?,?,?,?,?,?)",
        (
            body.source, body.name, body.em, body.cover, body.time, body.diff,
            jdump(body.tags), jdump([i.model_dump() for i in body.ing]),
            jdump(body.steps),
        ),
    )
    return {"id": cur.lastrowid, "ok": True}


@router.get("/{rid}")
def get_recipe(rid: int, conn: Connection = Depends(get_db)):
    return _get(conn, rid)


@router.put("/{rid}")
def update_recipe(rid: int, body: RecipePatch, conn: Connection = Depends(get_db)):
    """编辑菜谱。参考菜谱（source=admin）只读，禁止修改。"""
    rec = _get(conn, rid)
    if rec["source"] == "admin":
        raise HTTPException(403, "参考菜谱只读，不能编辑")
    data = body.model_dump(exclude_none=True)
    if "name" in data and data["name"] != rec["name"]:
        if _check_name_unique(conn, data["name"], exclude_id=rid):
            raise HTTPException(409, "我的菜谱已存在同名，请换个菜名")
    if "tags" in data:
        data["tags"] = jdump(data["tags"])
    if "ing" in data:
        data["ing"] = jdump([i.model_dump() if hasattr(i, "model_dump") else i for i in data["ing"]])
    if "steps" in data:
        data["steps"] = jdump(data["steps"])
    if not data:
        raise HTTPException(400, "没有可更新的字段")
    sets = ", ".join(f"{k}=?" for k in data)
    conn.execute(f"UPDATE recipes SET {sets} WHERE id=?", (*data.values(), rid))
    return {"id": rid, "ok": True}


@router.delete("/{rid}")
def delete_recipe(rid: int, conn: Connection = Depends(get_db)):
    """删除我的菜谱。参考菜谱只读，禁止删除。

    若该菜谱已在「吃这些」候选里，一并清理：回退其代入的待采购量
    （复用候选回退逻辑）并删除候选与计时，保持 COOK 一致。
    """
    rec = _get(conn, rid)
    if rec["source"] == "admin":
        raise HTTPException(403, "参考菜谱只读，不能删除")
    # 清理关联候选：先回退代入的待采购，再删候选与计时
    cand = conn.execute(
        "SELECT * FROM eat_inbox WHERE kind='recipe' AND ref_id=?", (rid,)
    ).fetchone()
    if cand:
        subs = jload(cand["subs"], default={})
        _subtract_subs(conn, subs)
        conn.execute("DELETE FROM tracks WHERE inbox_id=?", (cand["id"],))
        conn.execute("DELETE FROM eat_inbox WHERE id=?", (cand["id"],))
    conn.execute("DELETE FROM recipes WHERE id=?", (rid,))
    return {"id": rid, "ok": True}


@router.post("/{rid}/copy-to-mine")
def copy_to_mine(rid: int, conn: Connection = Depends(get_db)):
    """参考菜谱「存进我的菜谱」：复制一份 source=my 的新记录。"""
    rec = _get(conn, rid)
    cur = conn.execute(
        "INSERT INTO recipes(source,name,em,cover,time,diff,tags,ing,steps) "
        "VALUES('my',?,?,?,?,?,?,?,?)",
        (rec["name"], rec["em"], rec["cover"], rec["time"], rec["diff"],
         jdump(rec["tags"]), jdump(rec["ing"]), jdump(rec["steps"])),
    )
    return {"id": cur.lastrowid, "ok": True}