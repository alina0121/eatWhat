# -*- coding: utf-8 -*-
"""
食材库路由：双层模型——公共（scope=public）+ 用户私有补录（scope=user）。

核心规则：
- 公共层：管理员维护，所有用户可见，不能被用户同名补录。
- 用户私有层：用户自己补公共没有的，只限自己可见。
- 合并视图（默认 list）：public + 自己的 user，同名公共优先。
- 管理端（admin=true）：只看 public，改/删 public 项不做所有权校验。
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlite3 import Connection
from typing import Optional

from app.db import get_db, row_to_dict
from .auth import get_optional_user

router = APIRouter(prefix="/ingredients", tags=["ingredients"])


class IngredientIn(BaseModel):
    name: str
    cat: str = "其他"
    icon: str = ""  # 独立 emoji 图标（空=列表渲染回退用大类 icon）


def _merge_rows(conn: Connection, user_id: int) -> list:
    """返回 public + 当前用户私有，去重（public 优先）。"""
    rows = conn.execute(
        "SELECT * FROM ingredients WHERE scope='public' "
        "UNION ALL "
        "SELECT * FROM ingredients WHERE scope='user' AND user_id=? "
        "ORDER BY cat, name",
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
def list_ingredients(user: int = Depends(get_optional_user),
                     public_only: bool = Query(False, description="只返回公共层（管理端用）"),
                     conn: Connection = Depends(get_db)):
    """食材库清单。

    - public_only=False（默认）：公共 + 用户自己补录，合并去重。
    - public_only=True：只返回 scope='public'（管理端录入公共用）。
    """
    if public_only:
        rows = conn.execute(
            "SELECT * FROM ingredients WHERE scope='public' ORDER BY cat, name"
        ).fetchall()
        return [row_to_dict(r) for r in rows]
    return _merge_rows(conn, user)


def _check_name_public(conn: Connection, name: str) -> bool:
    """公共层是否已有同名食材。"""
    return conn.execute(
        "SELECT 1 FROM ingredients WHERE scope='public' AND name=?", (name,)
    ).fetchone() is not None


def _check_name_private(conn: Connection, name: str, user_id: int, exclude_id: Optional[int] = None) -> bool:
    """当前用户私有层是否已有同名食材。"""
    return conn.execute(
        "SELECT 1 FROM ingredients WHERE scope='user' AND user_id=? AND name=? AND id IS NOT ?",
        (user_id, name, exclude_id or -1),
    ).fetchone() is not None


@router.post("")
def create_ingredient(body: IngredientIn,
                      user: int = Depends(get_optional_user),
                      public: bool = Query(False, description="管理员录入公共层"),
                      conn: Connection = Depends(get_db)):
    """新增食材。public=False 为用户补录（scope=user），public=True 为管理员录入公共层。"""
    name = body.name.strip()
    if not name:
        raise HTTPException(422, "名称不能为空")

    if public:
        # 管理员录公共层：只跟公共层比不重
        if _check_name_public(conn, name):
            raise HTTPException(409, f"公共库已有「{name}」")
        cur = conn.execute(
            "INSERT INTO ingredients(scope,user_id,name,cat,icon) VALUES('public',1,?,?,?)",
            (name, body.cat, body.icon or ''),
        )
    else:
        # 用户补录：不能跟公共重名，也不能自己已有
        if _check_name_public(conn, name):
            raise HTTPException(409, f"公共库已有「{name}」，可直接选")
        if _check_name_private(conn, name, user):
            raise HTTPException(409, "你已经加过这个食材了")
        cur = conn.execute(
            "INSERT INTO ingredients(scope,user_id,name,cat,icon) VALUES('user',?,?,?,?)",
            (user, name, body.cat, body.icon or ''),
        )
    return {"id": cur.lastrowid, "ok": True}


@router.put("/{iid}")
def update_ingredient(iid: int, body: IngredientIn,
                      user: int = Depends(get_optional_user),
                      admin: bool = Query(False, description="管理员跳过所有权校验"),
                      conn: Connection = Depends(get_db)):
    """编辑食材。scope='public' 的改了名字要同步检查是否跟公共/私有重名。"""
    row = conn.execute("SELECT * FROM ingredients WHERE id=?", (iid,)).fetchone()
    if not row:
        raise HTTPException(404, "食材不存在")
    if row["scope"] == "public" and not admin:
        raise HTTPException(403, "公共食材不能直接改，请联系管理员")
    if row["scope"] == "user" and row["user_id"] != user:
        raise HTTPException(403, "无权修改他人食材")

    name = body.name.strip()
    if not name:
        raise HTTPException(422, "名称不能为空")

    # 改名时：不能撞公共层已有的、也不能撞自己私有层其他项
    if name != row["name"]:
        if _check_name_public(conn, name):
            raise HTTPException(409, f"公共库已有「{name}」")
        if _check_name_private(conn, name, user, exclude_id=iid):
            raise HTTPException(409, "你已经加过这个食材了")

    conn.execute(
        "UPDATE ingredients SET name=?, cat=?, icon=? WHERE id=?", (name, body.cat, body.icon or '', iid)
    )
    return {"id": iid, "ok": True}


@router.delete("/{iid}")
def delete_ingredient(iid: int,
                      user: int = Depends(get_optional_user),
                      admin: bool = Query(False, description="管理员可删公共层"),
                      conn: Connection = Depends(get_db)):
    """删除食材。公共层只有 admin=True 可删；私有层只能删自己的。"""
    row = conn.execute("SELECT * FROM ingredients WHERE id=?", (iid,)).fetchone()
    if not row:
        raise HTTPException(404, "食材不存在")
    if row["scope"] == "public" and not admin:
        raise HTTPException(403, "公共食材不能删，请联系管理员")
    if row["scope"] == "user" and row["user_id"] != user:
        raise HTTPException(403, "无权删除他人食材")
    conn.execute("DELETE FROM ingredients WHERE id=?", (iid,))
    return {"id": iid, "ok": True}
