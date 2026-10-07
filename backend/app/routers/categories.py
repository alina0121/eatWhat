# -*- coding: utf-8 -*-
"""
食材大类路由：双层模型——公共（scope=public）+ 用户私有补录（scope=user）。

规则与 ingredients 完全对齐：
- 公共层：管理员维护，所有用户可见，不能被用户同名补录。
- 用户私有层：补公共没有的，只限自己可见。
- list 默认返回合并视图；public_only=True 管理端只看公共。
- 改名级联 / 删除兜底 / 排序移动：只在当前 user 的可见范围生效。
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlite3 import Connection
from typing import Optional

from app.db import get_db, row_to_dict
from .auth import get_optional_user, get_write_user

router = APIRouter(prefix="/categories", tags=["categories"])

FALLBACK_CAT = "其他"


class CategoryIn(BaseModel):
    name: str
    icon: str = "🥗"


class CategoryMove(BaseModel):
    dir: str = "down"


def _merge_rows(conn: Connection, user_id: int) -> list:
    """返回 public + 当前用户私有，按 sort 排序（public 优先）。"""
    rows = conn.execute(
        "SELECT * FROM categories WHERE scope='public' "
        "UNION ALL "
        "SELECT * FROM categories WHERE scope='user' AND user_id=? "
        "ORDER BY sort, id",
        (user_id,),
    ).fetchall()
    seen = set()
    merged = []
    for r in rows:
        if r["name"] not in seen:
            seen.add(r["name"])
            merged.append(row_to_dict(r))
    return merged


@router.get("")
def list_categories(user: int = Depends(get_optional_user),
                    public_only: bool = Query(False),
                    conn: Connection = Depends(get_db)):
    if public_only:
        rows = conn.execute(
            "SELECT * FROM categories WHERE scope='public' ORDER BY sort, id"
        ).fetchall()
        return [row_to_dict(r) for r in rows]
    return _merge_rows(conn, user)


def _check_name_public(conn: Connection, name: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM categories WHERE scope='public' AND name=?", (name,)
    ).fetchone() is not None


def _check_name_private(conn: Connection, name: str, user_id: int, exclude_id: Optional[int] = None) -> bool:
    return conn.execute(
        "SELECT 1 FROM categories WHERE scope='user' AND user_id=? AND name=? AND id IS NOT ?",
        (user_id, name, exclude_id or -1),
    ).fetchone() is not None


def _ensure_fallback(conn: Connection, user_id: int) -> None:
    """兜底「其他」优先从公共层取；没有就给当前用户建一份私有兜底。"""
    if conn.execute(
        "SELECT 1 FROM categories WHERE scope='public' AND name=?", (FALLBACK_CAT,)
    ).fetchone() is None:
        if conn.execute(
            "SELECT 1 FROM categories WHERE scope='user' AND user_id=? AND name=?", (user_id, FALLBACK_CAT)
        ).fetchone() is None:
            _max = conn.execute(
                "SELECT COALESCE(MAX(sort),-1) FROM categories "
                "WHERE (scope='public' OR (scope='user' AND user_id=?))", (user_id,)
            ).fetchone()[0]
            conn.execute(
                "INSERT INTO categories(scope,user_id,name,icon,sort) VALUES('user',?,?,?,?)",
                (user_id, FALLBACK_CAT, "🥗", _max + 1),
            )


def _max_sort(conn: Connection, user_id: int) -> int:
    return conn.execute(
        "SELECT COALESCE(MAX(sort),-1) FROM categories "
        "WHERE (scope='public' OR (scope='user' AND user_id=?))", (user_id,)
    ).fetchone()[0]


@router.post("")
def create_category(body: CategoryIn,
                    user: int = Depends(get_write_user),
                    public: bool = Query(False),
                    conn: Connection = Depends(get_db)):
    name = body.name.strip()
    if not name:
        raise HTTPException(422, "名称不能为空")

    if public:
        if _check_name_public(conn, name):
            raise HTTPException(409, f"公共层已有「{name}」")
        cur = conn.execute(
            "INSERT INTO categories(scope,user_id,name,icon,sort) VALUES('public',1,?,?,?)",
            (name, body.icon or "🥗", _max_sort(conn, user) + 1),
        )
    else:
        if _check_name_public(conn, name):
            raise HTTPException(409, f"公共层已有「{name}」")
        if _check_name_private(conn, name, user):
            raise HTTPException(409, "你已经加过这个大类了")
        cur = conn.execute(
            "INSERT INTO categories(scope,user_id,name,icon,sort) VALUES('user',?,?,?,?)",
            (user, name, body.icon or "🥗", _max_sort(conn, user) + 1),
        )
    return {"id": cur.lastrowid, "ok": True}


def _get_row(conn: Connection, cid: int, user_id: int, admin: bool) -> Optional[dict]:
    row = conn.execute("SELECT * FROM categories WHERE id=?", (cid,)).fetchone()
    if not row:
        return None
    if row["scope"] == "public" and not admin:
        raise HTTPException(403, "公共大类不能改，请联系管理员")
    if row["scope"] == "user" and row["user_id"] != user_id:
        raise HTTPException(403, "无权操作他人大类")
    return row_to_dict(row)


@router.put("/{cid}")
def update_category(cid: int, body: CategoryIn,
                    user: int = Depends(get_write_user),
                    admin: bool = Query(False),
                    conn: Connection = Depends(get_db)):
    row = _get_row(conn, cid, user, admin)
    if not row:
        raise HTTPException(404, "大类不存在")

    name = body.name.strip()
    if not name:
        raise HTTPException(422, "名称不能为空")

    if name != row["name"]:
        if _check_name_public(conn, name):
            raise HTTPException(409, f"公共层已有「{name}」")
        if _check_name_private(conn, name, user, exclude_id=cid):
            raise HTTPException(409, "你已经加过这个大类了")

    old = row["name"]
    conn.execute(
        "UPDATE categories SET name=?, icon=? WHERE id=?", (name, body.icon or "🥗", cid)
    )
    # 级联改名：只动当前用户的 ingredients / fridge_items（它们 cat 字段存的是名字）
    if old != name:
        conn.execute(
            "UPDATE ingredients SET cat=? WHERE user_id=? AND cat=?", (name, user, old)
        )
        conn.execute(
            "UPDATE fridge_items SET cat=? WHERE user_id=? AND cat=?", (name, user, old)
        )
    return {"id": cid, "ok": True}


@router.post("/{cid}/move")
def move_category(cid: int, body: CategoryMove,
                  user: int = Depends(get_write_user),
                  admin: bool = Query(False),
                  conn: Connection = Depends(get_db)):
    row = _get_row(conn, cid, user, admin)
    if not row:
        raise HTTPException(404, "大类不存在")
    direction = -1 if body.dir == "up" else 1
    cmp_ = ">" if direction == 1 else "<"
    # 只在自己可见的（public + 自己 private）里找相邻项
    nxt = conn.execute(
        f"SELECT * FROM categories "
        f"WHERE (scope='public' AND sort {cmp_} ?) OR "
        f"      (scope='user' AND user_id=? AND sort {cmp_} ?) "
        f"ORDER BY sort {'ASC' if direction == 1 else 'DESC'} LIMIT 1",
        (row["sort"], user, row["sort"]),
    ).fetchone()
    if not nxt:
        return {"id": cid, "ok": True}
    conn.execute("UPDATE categories SET sort=? WHERE id=?", (nxt["sort"], cid))
    conn.execute("UPDATE categories SET sort=? WHERE id=?", (row["sort"], nxt["id"]))
    return {"id": cid, "ok": True}


@router.delete("/{cid}")
def delete_category(cid: int,
                    user: int = Depends(get_write_user),
                    admin: bool = Query(False),
                    conn: Connection = Depends(get_db)):
    row = _get_row(conn, cid, user, admin)
    if not row:
        raise HTTPException(404, "大类不存在")
    name = row["name"]
    _ensure_fallback(conn, user)
    # 兜底优先公共层；如果公共层没「其他」用自己私有层的
    fb = conn.execute(
        "SELECT name FROM categories "
        "WHERE (scope='public' OR (scope='user' AND user_id=?)) AND name=? "
        "LIMIT 1", (user, FALLBACK_CAT)
    ).fetchone()
    fb_name = fb["name"] if fb else FALLBACK_CAT
    conn.execute(
        "UPDATE ingredients SET cat=? WHERE user_id=? AND cat=?", (fb_name, user, name)
    )
    conn.execute(
        "UPDATE fridge_items SET cat=? WHERE user_id=? AND cat=?", (fb_name, user, name)
    )
    conn.execute("DELETE FROM categories WHERE id=?", (cid,))
    return {"id": cid, "ok": True}
