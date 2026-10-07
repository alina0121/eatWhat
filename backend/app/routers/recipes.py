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
from app.routers.auth import get_optional_user, get_write_user
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


def _get_owned(conn: Connection, rid: int, user: int) -> dict:
    """取菜谱并校验归属：参考菜谱（source=admin）是公共内容，人人可读；
    我的菜谱只有作者本人能读/改/删，避免 A 用户看到或改到 B 用户的菜谱。"""
    rec = _get(conn, rid)
    if rec["source"] == "my" and rec.get("user_id") != user:
        raise HTTPException(404, "菜谱不存在")
    return rec


def _enrich_cover(conn: Connection, d: dict) -> dict:
    """cover 字段直接存渐变字符串（或空=默认轮换），解析后返回 coverGrad。"""
    raw = d.get("cover") or ""
    if raw:
        # 兼容旧格式 "emoji|grad"：只取 grad 部分
        if "|" in raw:
            d["coverGrad"] = raw.split("|", 1)[1] or ""
        else:
            d["coverGrad"] = raw
    return d


@router.get("")
def list_recipes(source: Optional[str] = None,
                 user: int = Depends(get_optional_user),
                 conn: Connection = Depends(get_db)):
    """按来源筛选菜谱。

    隔离规则：参考菜谱（source=admin）是公共内容人人可见；
    我的菜谱只返回当前登录用户自己的，避免看到别人的菜谱。
    未登录（user=0）时只能看到参考菜谱。
    """
    if source == "admin":
        rows = conn.execute(
            "SELECT * FROM recipes WHERE source='admin' ORDER BY id DESC"
        ).fetchall()
    elif source == "my":
        rows = conn.execute(
            "SELECT * FROM recipes WHERE source='my' AND user_id=? ORDER BY id DESC",
            (user,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM recipes WHERE source='admin' OR (source='my' AND user_id=?) "
            "ORDER BY id DESC",
            (user,),
        ).fetchall()
    return [_enrich_cover(conn, row_to_dict(r)) for r in rows]


def _check_name_unique(conn: Connection, name: str, user: int,
                       exclude_id: Optional[int] = None):
    """同一用户的「我的菜谱」不允许同名（别人有同名的无所谓）。返回冲突 id 或 None。"""
    row = conn.execute(
        "SELECT id FROM recipes WHERE source='my' AND user_id=? AND name=? AND id IS NOT ?",
        (user, name, exclude_id or -1),
    ).fetchone()
    return row["id"] if row else None


@router.post("")
def create_recipe(body: RecipeIn,
                  user: int = Depends(get_write_user),
                  conn: Connection = Depends(get_db)):
    """新建菜谱（默认我的菜谱；写 source=admin 即录入参考菜谱）。"""
    if body.source == "my" and _check_name_unique(conn, body.name, user):
        raise HTTPException(409, "我的菜谱已存在同名，请换个菜名")
    cur = conn.execute(
        "INSERT INTO recipes(user_id,source,name,em,cover,time,diff,tags,ing,steps) "
        "VALUES(?,?,?,?,?,?,?,?,?,?)",
        (
            user, body.source, body.name, body.em, body.cover, body.time, body.diff,
            jdump(body.tags), jdump([i.model_dump() for i in body.ing]),
            jdump(body.steps),
        ),
    )
    return {"id": cur.lastrowid, "ok": True}


@router.get("/{rid}")
def get_recipe(rid: int,
               user: int = Depends(get_optional_user),
               conn: Connection = Depends(get_db)):
    return _get_owned(conn, rid, user)


@router.put("/{rid}")
def update_recipe(rid: int, body: RecipePatch,
                  user: int = Depends(get_write_user),
                  conn: Connection = Depends(get_db)):
    """编辑菜谱。参考菜谱（source=admin）由管理端编辑，同样放行；名称唯一校验仅针对我的菜谱。"""
    rec = _get_owned(conn, rid, user)
    data = body.model_dump(exclude_none=True)
    if "name" in data and data["name"] != rec["name"]:
        if _check_name_unique(conn, data["name"], user, exclude_id=rid):
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
def delete_recipe(rid: int,
                  user: int = Depends(get_write_user),
                  conn: Connection = Depends(get_db)):
    """删除菜谱（我的或参考菜谱均可，由管理端对 admin 源操作）。

    若该菜谱已在「吃这些」候选里，一并清理：回退其代入的待采购量
    （复用候选回退逻辑）并删除候选与计时，保持 COOK 一致。
    候选与待采购都按 user_id 隔离，只清理当前用户自己的那份。
    """
    _get_owned(conn, rid, user)
    # 清理关联候选：先回退代入的待采购，再删候选与计时
    cand = conn.execute(
        "SELECT * FROM eat_inbox WHERE kind='recipe' AND ref_id=? AND user_id=?",
        (rid, user),
    ).fetchone()
    if cand:
        subs = jload(cand["subs"], default={})
        _subtract_subs(conn, subs, user)
        conn.execute("DELETE FROM tracks WHERE inbox_id=?", (cand["id"],))
        conn.execute("DELETE FROM eat_inbox WHERE id=?", (cand["id"],))
    conn.execute("DELETE FROM recipes WHERE id=?", (rid,))
    return {"id": rid, "ok": True}


@router.post("/{rid}/copy-to-mine")
def copy_to_mine(rid: int,
                 user: int = Depends(get_write_user),
                 conn: Connection = Depends(get_db)):
    """参考菜谱「存进我的菜谱」：复制一份 source=my 的新记录，归属当前用户。

    若该用户已存在同名的「我的菜谱」，返回 409 提示前端。
    """
    rec = _get_owned(conn, rid, user)
    if _check_name_unique(conn, rec["name"], user):
        raise HTTPException(409, f"已存在同名菜谱「{rec['name']}」，请换个名字或直接编辑它")
    cur = conn.execute(
        "INSERT INTO recipes(user_id,source,name,em,cover,time,diff,tags,ing,steps) "
        "VALUES(?,'my',?,?,?,?,?,?,?,?)",
        (user, rec["name"], rec["em"], rec["cover"], rec["time"], rec["diff"],
         jdump(rec["tags"]), jdump(rec["ing"]), jdump(rec["steps"])),
    )
    return {"id": cur.lastrowid, "ok": True}