# -*- coding: utf-8 -*-
"""
用户端「我的数据」总览路由：
- /mine/stats: 个人数据聚合（计数卡 + 本月干饭分布 + 体重趋势），后端现算，前端只消费结果。

设计要点：
- 个人数据（我的菜谱/冰箱/干饭/体重/餐厅收藏等）只在用户端展示，不上管理端（管理端只做公共资源）。
- 一切派生统计实时现算，不落冗余存储。
- 全部按当前登录用户 user_id 过滤；未登录（user=0）时计数为 0、趋势为空。
"""
from fastapi import APIRouter, Depends
from sqlite3 import Connection
from datetime import date

from app.db import get_db
from app.routers.auth import get_optional_user

router = APIRouter(prefix="/mine", tags=["mine"])


@router.get("/stats")
def mine_stats(user: int = Depends(get_optional_user),
               conn: Connection = Depends(get_db)):
    """个人数据总览：计数卡片 + 本月干饭分布 + 体重趋势（均限当前用户）。"""
    def cnt(sql, *args):
        return conn.execute(sql, args).fetchone()[0]

    month = date.today().strftime("%Y-%m")

    cards = {
        # 我的菜谱按人隔离；参考菜谱是公共内容，人人一样
        "recipes_my": cnt("SELECT COUNT(*) FROM recipes WHERE source='my' AND user_id=?", user),
        "recipes_ref": cnt("SELECT COUNT(*) FROM recipes WHERE source='admin'"),
        "fridge_in": cnt("SELECT COUNT(*) FROM fridge_items WHERE user_id=?", user),
        "purchase": cnt("SELECT COUNT(*) FROM purchase WHERE user_id=?", user),
        "inbox": cnt("SELECT COUNT(*) FROM eat_inbox WHERE user_id=?", user),
        "shops": cnt("SELECT COUNT(*) FROM shops WHERE user_id=?", user),
        "records_total": cnt("SELECT COUNT(*) FROM records WHERE user_id=?", user),
        "weights": cnt("SELECT COUNT(*) FROM weights WHERE user_id=?", user),
    }

    # 本月干饭分布（按 type）
    type_map = {"delivery": "外卖", "out": "餐厅", "cook": "自做"}
    dist = [{"type": k, "label": type_map.get(k, k), "count": 0}
            for k in ("cook", "out", "delivery")]
    for row in conn.execute(
        "SELECT type, COUNT(*) AS c FROM records WHERE user_id=? AND date LIKE ? GROUP BY type",
        (user, month + "%"),
    ):
        for d in dist:
            if d["type"] == row["type"]:
                d["count"] = row["c"]
    dist = [d for d in dist if d["count"] > 0]

    # 体重趋势：最近 10 条（旧→新）
    trend = [
        {"date": r["date"], "weight": r["weight"]}
        for r in conn.execute(
            "SELECT date, weight FROM weights WHERE user_id=? ORDER BY date DESC LIMIT 10",
            (user,),
        )
    ][::-1]

    return {"cards": cards, "monthly": {"month": month, "dist": dist}, "weight_trend": trend}