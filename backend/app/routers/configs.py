# -*- coding: utf-8 -*-
"""
配置表路由：统一读写环境参数（审核开关、临期阈值等）。
配置不散落在代码里，运维只要改数据库键值即可。
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlite3 import Connection

from app.db import get_db

router = APIRouter(prefix="/configs", tags=["configs"])


class ConfigIn(BaseModel):
    value: str


def get_config(conn: Connection, key: str, default: str = "") -> str:
    """读单个配置的便捷函数，供其它模块复用。"""
    row = conn.execute("SELECT value FROM configs WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_config(conn: Connection, key: str, value: str) -> None:
    """写单个配置（存在则更新，不存在则插入）。"""
    conn.execute(
        "INSERT INTO configs(key,value) VALUES(?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )


@router.get("")
def list_configs(conn: Connection = Depends(get_db)):
    """返回全部配置（key/value 键值对）。"""
    rows = conn.execute("SELECT key, value FROM configs ORDER BY key").fetchall()
    return [{"key": r["key"], "value": r["value"]} for r in rows]


@router.get("/{key}")
def get_one(key: str, conn: Connection = Depends(get_db)):
    """读单个配置，不存在返回 404。"""
    row = conn.execute("SELECT value FROM configs WHERE key=?", (key,)).fetchone()
    if not row:
        raise HTTPException(404, f"配置不存在: {key}")
    return {"key": key, "value": row["value"]}


@router.put("/{key}")
def update_config(key: str, body: ConfigIn, conn: Connection = Depends(get_db)):
    """写单个配置（新增或更新）。"""
    set_config(conn, key, body.value)
    return {"key": key, "value": body.value, "ok": True}