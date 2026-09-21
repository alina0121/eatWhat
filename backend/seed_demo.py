# -*- coding: utf-8 -*-
"""
演示数据种子脚本（幂等）：为空表注入一批可直接验收用的数据。

用法：cd backend && python seed_demo.py
仅当对应表为空时写入，重复执行不会产生重复数据。
"""
from app.db import get_conn, init_db, jdump

def main():
    init_db()
    conn = get_conn()
    try:
        # ---- 菜谱（我的）----
        if conn.execute("SELECT COUNT(*) c FROM recipes").fetchone()["c"] == 0:
            recipes = [
                # 缺番茄/鸡蛋：加候选会自动代入待采购
                ["my", "番茄炒蛋", "🍅", 15, "简单", ["下饭", "咸鲜"],
                 [{"name": "番茄", "qty": 2, "unit": "个"}, {"name": "鸡蛋", "qty": 3, "unit": "个"}],
                 ["番茄切块", "鸡蛋打散炒熟盛出", "下番茄翻炒，调味", "回锅鸡蛋翻匀"]],
                ["my", "麻婆豆腐", "🌶", 25, "一般", ["辣", "下饭"],
                 [{"name": "豆腐", "qty": 2, "unit": "盒"}, {"name": "肉末", "qty": 1, "unit": "份"}, {"name": "豆瓣酱", "qty": 1, "unit": "勺"}],
                 ["煸炒肉末", "加豆瓣酱炒出红油", "下豆腐加水焖", "淀粉收汁"]],
                ["my", "清蒸鲈鱼", "🐟", 30, "较难", ["清淡", "鲜"],
                 [{"name": "鲈鱼", "qty": 1, "unit": "条"}, {"name": "姜", "qty": 1, "unit": "块"}],
                 ["鲈鱼改刀", "铺姜旺火蒸8分钟", "淋豉油热油"]],
                # 参考菜谱（管理员录入，只读）
                ["admin", "宫保鸡丁", "🥜", 20, "一般", ["辣", "下饭"],
                 [{"name": "鸡腿肉", "qty": 2, "unit": "块"}, {"name": "花生米", "qty": 1, "unit": "份"}],
                 ["鸡丁上浆滑熟", "爆香干辣椒", "下料汁翻炒", "入花生颠锅"]],
            ]
            conn.executemany(
                "INSERT INTO recipes(source,name,em,time,diff,tags,ing,steps) VALUES(?,?,?,?,?,?,?,?)",
                [(s, n, e, t, d, jdump(tags), jdump(ing), jdump(steps)) for s, n, e, t, d, tags, ing, steps in recipes],
            )
            print("已写入菜谱 x%d" % len(recipes))

        # ---- 在库冰箱（番茄只存1个 → 加番茄炒蛋候选会缺1个番茄）----
        if conn.execute("SELECT COUNT(*) c FROM fridge_items").fetchone()["c"] == 0:
            items = [
                ("番茄", "蔬菜", 1, "个", "冷藏", 6),
                ("鸡蛋", "肉类", 6, "个", "冷藏", 21),
                ("豆腐", "其他", 0, "盒", "", 3),   # 已无库存
            ]
            conn.executemany(
                "INSERT INTO fridge_items(name,cat,qty,unit,store,days) VALUES(?,?,?,?,?,?)", items,
            )
            print("已写入在库 x%d" % len(items))

        # ---- 干饭成员（口味联动）----
        if conn.execute("SELECT COUNT(*) c FROM diners").fetchone()["c"] == 0:
            conn.executemany(
                "INSERT INTO diners(name,tags) VALUES(?,?)",
                [("小明", jdump(["辣", "不吃香菜"])), ("小红", jdump(["微辣", "清淡"]))],
            )
            print("已写入干饭成员 x2")

        # ---- 餐厅收藏 ----
        if conn.execute("SELECT COUNT(*) c FROM shops").fetchone()["c"] == 0:
            shops = [
                ("好辣川菜", "川菜", "￥80", 4.5, ["水煮鱼", "辣子鸡"], 20, "骑车", ["辣", "下饭"]),
                ("轻食沙拉", "轻食", "￥45", 4.8, ["鸡胸沙拉"], 10, "步行", ["清淡"]),
            ]
            conn.executemany(
                "INSERT INTO shops(name,type,price,star,must,arr_min,transport,tags) VALUES(?,?,?,?,?,?,?,?)",
                [(n, t, p, s, jdump(m), a, tr, jdump(tag)) for n, t, p, s, m, a, tr, tag in shops],
            )
            print("已写入餐厅 x%d" % len(shops))

        # ---- 体重记录 ----
        if conn.execute("SELECT COUNT(*) c FROM weights").fetchone()["c"] == 0:
            conn.executemany(
                "INSERT INTO weights(date,weight,body_fat) VALUES(?,?,?)",
                [("2026-09-15", 66.5, 21.0), ("2026-09-17", 66.2, 20.8), ("2026-09-19", 65.9, 20.5)],
            )
            print("已写入体重 x3")

        # ---- 厨房技巧（一条待审 + 一条已公开）----
        if conn.execute("SELECT COUNT(*) c FROM tips").fetchone()["c"] == 0:
            conn.executemany(
                "INSERT INTO tips(title,content,cat,author,pub,status) VALUES(?,?,?,?,?,?)",
                [
                    ("焯水去腥", "冷水下锅加姜片葱段，水开即捞。", "烹饪", "小明", 1, "approved"),
                    ("炒肉嫩滑秘诀", "先加少许淀粉腌制十分钟。", "烹饪", "小红", 1, "pending"),
                ],
            )
            print("已写入厨房技巧 x2")

        conn.commit()
        print("演示数据已就绪 ✅")
    finally:
        conn.close()

if __name__ == "__main__":
    main()