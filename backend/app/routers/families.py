# -*- coding: utf-8 -*-
"""
家庭空间路由：把「吃这些」候选池共享给家人（对齐下厨房家庭库式交互）。

交互流程：
- 创建家庭空间 → 生成 6 位邀请码，创建者自动入会。
- 对方在「家庭」页粘贴邀请码加入 → 共享同一份候选池（candidates space=family）。
- 一人一家庭：加入/创建前必须先退出当前家庭。
- 退出：普通成员仅退自己；创建者退出 = 解散（清成员 + 清该家庭候选池含计时）。

候选池的读写与记账见 candidates.py（家庭池内人人可见、可加/删/启停计时，
缺货代入与回退始终按「加者」的 fridge/purchase 记账）。
"""
import random

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlite3 import Connection

from app.db import get_db
from .auth import get_current_user

router = APIRouter(prefix="/families", tags=["families"])

# 邀请码字符集：6 位大写字母数字，去掉易混淆的 0/O/1/I
_CODE_CHARS = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"


class FamilyIn(BaseModel):
    name: str


class JoinIn(BaseModel):
    code: str


def _gen_code(conn: Connection) -> str:
    """生成不冲突的 6 位邀请码。"""
    while True:
        code = "".join(random.choice(_CODE_CHARS) for _ in range(6))
        if not conn.execute("SELECT 1 FROM families WHERE code=?", (code,)).fetchone():
            return code


def _my_family_row(conn: Connection, uid: int):
    """取该用户所在家庭行；未加入返回 None。"""
    return conn.execute(
        "SELECT f.* FROM families f JOIN family_members m ON m.family_id=f.id WHERE m.user_id=?",
        (uid,),
    ).fetchone()


def _payload(conn: Connection, fam) -> dict:
    """家庭信息 + 成员列表（昵称/头像，供家庭页展示）。"""
    members = conn.execute(
        "SELECT m.user_id, u.nickname, u.avatar FROM family_members m "
        "JOIN users u ON u.id=m.user_id WHERE m.family_id=? ORDER BY m.id",
        (fam["id"],),
    ).fetchall()
    return {
        "id": fam["id"],
        "code": fam["code"],
        "name": fam["name"],
        "owner_id": fam["owner_id"],
        "members": [dict(m) for m in members],
    }


def _assert_not_in_family(conn: Connection, uid: int):
    """一人一家庭：已在家庭里则禁止创建/再加入。"""
    if conn.execute("SELECT 1 FROM family_members WHERE user_id=?", (uid,)).fetchone():
        raise HTTPException(400, "你已在一个家庭空间里，请先退出后再创建或加入")


@router.get("/mine")
def my_family(user: int = Depends(get_current_user), conn: Connection = Depends(get_db)):
    """我的家庭空间（含邀请码与成员列表）。未加入返回 {family: null}。"""
    fam = _my_family_row(conn, user)
    return {"family": _payload(conn, fam) if fam else None}


@router.post("")
def create_family(body: FamilyIn, user: int = Depends(get_current_user), conn: Connection = Depends(get_db)):
    """创建家庭空间：起个名字，生成邀请码，创建者自动入会。"""
    name = (body.name or "").strip()[:20]
    if not name:
        raise HTTPException(400, "先给家庭空间起个名字吧")
    _assert_not_in_family(conn, user)
    code = _gen_code(conn)
    cur = conn.execute(
        "INSERT INTO families(code,name,owner_id) VALUES(?,?,?)", (code, name, user)
    )
    fam = conn.execute("SELECT * FROM families WHERE id=?", (cur.lastrowid,)).fetchone()
    conn.execute("INSERT INTO family_members(family_id,user_id) VALUES(?,?)", (fam["id"], user))
    return _payload(conn, fam)


@router.post("/join")
def join_family(body: JoinIn, user: int = Depends(get_current_user), conn: Connection = Depends(get_db)):
    """凭 6 位邀请码加入对方的家庭空间。"""
    code = (body.code or "").strip().upper()
    if not code:
        raise HTTPException(400, "请输入 6 位家庭 ID")
    fam = conn.execute("SELECT * FROM families WHERE code=?", (code,)).fetchone()
    if not fam:
        raise HTTPException(404, "家庭 ID 不存在，请让对方确认后再试")
    _assert_not_in_family(conn, user)
    conn.execute(
        "INSERT INTO family_members(family_id,user_id) VALUES(?,?)", (fam["id"], user)
    )
    return _payload(conn, fam)


@router.post("/leave")
def leave_family(user: int = Depends(get_current_user), conn: Connection = Depends(get_db)):
    """退出家庭空间。创建者退出 = 解散：清成员、清该家庭候选池（含计时）。"""
    m = conn.execute("SELECT * FROM family_members WHERE user_id=?", (user,)).fetchone()
    if not m:
        raise HTTPException(404, "你还没有加入家庭空间")
    fam = conn.execute("SELECT * FROM families WHERE id=?", (m["family_id"],)).fetchone()
    if fam and fam["owner_id"] == user:
        # 解散：家庭池候选连带的计时先摘掉，再清候选、成员、家庭
        conn.execute(
            "DELETE FROM tracks WHERE inbox_id IN (SELECT id FROM eat_inbox WHERE family_id=?)",
            (fam["id"],),
        )
        conn.execute("DELETE FROM eat_inbox WHERE family_id=?", (fam["id"],))
        conn.execute("DELETE FROM family_members WHERE family_id=?", (fam["id"],))
        conn.execute("DELETE FROM families WHERE id=?", (fam["id"],))
        return {"ok": True, "dissolved": True}
    conn.execute("DELETE FROM family_members WHERE user_id=?", (user,))
    return {"ok": True, "dissolved": False}
