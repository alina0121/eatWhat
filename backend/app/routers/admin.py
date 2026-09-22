# -*- coding: utf-8 -*-
"""
管理端路由：
- /admin/login: 密码登录（passcode 存配置表 admin_passcode），仅门控管理端，不影响移动端。
- /admin/stats: 统计仪表盘所需聚合数据，后端现算派生，前端只消费结果。

设计要点：鉴权只保护管理端入口，移动端/其余全 API 不设登录门槛（MVP 语义）。
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlite3 import Connection

from app.db import get_db, row_to_dict, jload
from app.routers.configs import get_config, set_config

router = APIRouter(prefix="/admin", tags=["admin"])


class LoginIn(BaseModel):
    code: str


@router.post("/login")
def admin_login(body: LoginIn, conn: Connection = Depends(get_db)):
    """校验管理端口令。通过返回 ok，前端存会话标记解锁管理台。"""
    pwd = get_config(conn, "admin_passcode", "123456")
    if body.code != pwd:
        raise HTTPException(401, "口令错误")
    return {"ok": True}


@router.get("/stats")
def admin_stats(conn: Connection = Depends(get_db)):
    """统计仪表盘聚合：计数卡片 + 本月干饭分布 + 体重趋势（原始数据现算，不落冗余）。"""
    import datetime

    def cnt(sql, *args):
        return conn.execute(sql, args).fetchone()[0]

    today = datetime.date.today()
    month = today.strftime("%Y-%m")

    # 计数卡片
    cards = {
        "recipes_my": cnt("SELECT COUNT(*) FROM recipes WHERE source='my'"),
        "recipes_ref": cnt("SELECT COUNT(*) FROM recipes WHERE source='admin'"),
        "ingredients": cnt("SELECT COUNT(*) FROM ingredients"),
        "fridge_in": cnt("SELECT COUNT(*) FROM fridge_items"),
        "purchase": cnt("SELECT COUNT(*) FROM purchase"),
        "shops": cnt("SELECT COUNT(*) FROM shops"),
        "tips_pending": cnt("SELECT COUNT(*) FROM tips WHERE status='pending'"),
        "records_total": cnt("SELECT COUNT(*) FROM records"),
    }

    # 本月干饭分布（按 type）
    type_map = {"delivery": "外卖", "out": "餐厅", "cook": "自做"}
    dist = [
        {"type": k, "label": type_map.get(k, k), "count": 0}
        for k in ("cook", "out", "delivery")
    ]
    for row in conn.execute(
        "SELECT type, COUNT(*) AS c FROM records WHERE date LIKE ? GROUP BY type",
        (month + "%",),
    ):
        for d in dist:
            if d["type"] == row["type"]:
                d["count"] = row["c"]
    dist = [d for d in dist if d["count"] > 0]

    # 体重趋势：最近 10 条
    trend = [
        {"date": r["date"], "weight": r["weight"]}
        for r in conn.execute(
            "SELECT date, weight FROM weights ORDER BY date DESC LIMIT 10"
        ).fetchall()
    ][::-1]

    # 待审核技巧 + 参考菜谱数
    return {"cards": cards, "monthly": {"month": month, "dist": dist}, "weight_trend": trend}