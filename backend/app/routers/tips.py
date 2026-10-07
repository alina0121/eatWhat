# -*- coding: utf-8 -*-
"""
厨房技巧路由（内容社区 + 审核闭环）。

权限模型（对齐第一版基准 / 项目硬约束）：
- 所有人可见、都能新增；只能修改 / 删除自己创建的技巧。
- 新增 / 编辑一律进入待审核（pending）；管理员「通过」→ approved /「退回」→ rejected。
- 未通过审核的内容仅创建者自己可见；已通过且公开(pub=1) 才对所有人可见。
- 是否走审核由配置表 audit_enabled 控制：关闭时新增 / 编辑直接 approved（演示/自用便捷）。

归属判定用 user_id（登录态决定），不再用 author 名字字符串——
名字可重名，且前端传什么就信什么，等于没有权限校验；author 现在仅用于展示。
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlite3 import Connection

from app.db import get_db, row_to_dict
from app.routers.auth import get_optional_user, get_write_user
from app.routers.configs import get_config
from app.wxsec import check_text

router = APIRouter(prefix="/tips", tags=["tips"])


class TipIn(BaseModel):
    title: str
    content: str
    cat: str = "其他"
    author: str = ""     # 作者名（仅展示用，归属以 user_id 为准）
    pub: bool = True     # 是否公开


def _initial_status(conn: Connection) -> str:
    """审核开关关掉时直接放行（approved），否则进入 pending。"""
    return "pending" if get_config(conn, "audit_enabled", "1") == "1" else "approved"


def _get(conn: Connection, tid: int):
    row = conn.execute("SELECT * FROM tips WHERE id=?", (tid,)).fetchone()
    if not row:
        raise HTTPException(404, "技巧不存在")
    return row_to_dict(row)


def list_visible_sql(user: int, only_status: Optional[str] = None) -> tuple:
    """拼可见性过滤条件：自己的一条不漏；他人只有「已通过且公开」才可见。

    可选 only_status 供管理员按状态批量审核。
    """
    conds = ["(user_id = ?) OR (status = 'approved' AND pub = 1)"]
    args = [user]
    if only_status:
        conds.append("status = ?")
        args.append(only_status)
    return " AND ".join(conds), args


@router.get("")
def list_tips(
    only_status: Optional[str] = None,
    admin: bool = False,
    user: int = Depends(get_optional_user),
    conn: Connection = Depends(get_db),
):
    """列技巧。当前登录用户自己的内容全可见，他人只看到已公开通过的。

    admin=True 时返回全部（含他人未审核/私密的），供管理端审核用。
    """
    if admin:
        if only_status:
            rows = conn.execute(
                "SELECT * FROM tips WHERE status=? ORDER BY id DESC", (only_status,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM tips ORDER BY id DESC").fetchall()
        return [row_to_dict(r) for r in rows]
    cond, args = list_visible_sql(user, only_status)
    rows = conn.execute(
        f"SELECT * FROM tips WHERE {cond} ORDER BY id DESC", args
    ).fetchall()
    return [row_to_dict(r) for r in rows]


@router.post("")
def create_tip(body: TipIn,
               user: int = Depends(get_write_user),
               conn: Connection = Depends(get_db)):
    """新增技巧：先过微信内容安全检测（启用时），再进入待审核（或直接通过，视开关）。"""
    # 标题也可能是违规内容，与正文合并送检
    ok, reason = check_text(conn, f"{body.title}\n{body.content}")
    if not ok:
        raise HTTPException(400, reason)
    status = _initial_status(conn)
    cur = conn.execute(
        "INSERT INTO tips(user_id,title,content,cat,author,pub,status) VALUES(?,?,?,?,?,?,?)",
        (user, body.title, body.content, body.cat, body.author, int(body.pub), status),
    )
    return {"id": cur.lastrowid, "status": status, "ok": True}


@router.put("/{tid}")
def update_tip(tid: int, body: TipIn,
               user: int = Depends(get_write_user),
               conn: Connection = Depends(get_db)):
    """编辑技巧：只能改自己的；改后需重新审核（除非开关关闭直接通过）。"""
    tip = _get(conn, tid)
    if tip["user_id"] != user:
        raise HTTPException(403, "只能修改自己创建的技巧")
    ok, reason = check_text(conn, f"{body.title}\n{body.content}")
    if not ok:
        raise HTTPException(400, reason)
    status = _initial_status(conn)
    # 展示名允许作者自己改，归属列 user_id 不动
    conn.execute(
        "UPDATE tips SET title=?,content=?,cat=?,author=?,pub=?,status=?,"
        "updated_at=datetime('now','localtime') WHERE id=?",
        (body.title, body.content, body.cat, body.author or tip["author"],
         int(body.pub), status, tid),
    )
    return {"id": tid, "status": status, "ok": True}


@router.delete("/{tid}")
def delete_tip(tid: int,
               user: int = Depends(get_write_user),
               conn: Connection = Depends(get_db)):
    """删除技巧：只能删自己的（按 user_id 判定归属）。"""
    tip = _get(conn, tid)
    if tip["user_id"] != user:
        raise HTTPException(403, "只能删除自己创建的技巧")
    conn.execute("DELETE FROM tips WHERE id=?", (tid,))
    return {"id": tid, "ok": True}


# ---------------------------------------------------------------------------
# 管理员审核
# ---------------------------------------------------------------------------
@router.post("/{tid}/approve")
def approve_tip(tid: int, conn: Connection = Depends(get_db),
                _admin: int = Depends(get_write_user)):
    """管理员通过 → approved，公开展示。"""
    _get(conn, tid)
    conn.execute("UPDATE tips SET status='approved', updated_at=datetime('now','localtime') WHERE id=?", (tid,))
    return {"id": tid, "status": "approved", "ok": True}


@router.post("/{tid}/reject")
def reject_tip(tid: int, conn: Connection = Depends(get_db),
               _admin: int = Depends(get_write_user)):
    """管理员退回 → rejected，仅作者可见。"""
    _get(conn, tid)
    conn.execute("UPDATE tips SET status='rejected', updated_at=datetime('now','localtime') WHERE id=?", (tid,))
    return {"id": tid, "status": "rejected", "ok": True}