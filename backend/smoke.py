# -*- coding: utf-8 -*-
"""冒烟测试：导入全部应用、建表、列出所有数据表，并跑一遍核心业务链路。

用法：cd backend && python smoke.py
"""
import sqlite3

# 1. 导入应用（会执行 init_db 建表+种子）
import app.main  # noqa: F401
import app.db as db

print("[1] 应用导入 OK")

# 2. 列所有表
conn = db.get_conn()
tables = [r[0] for r in conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
).fetchall()]
print("[2] 数据表:", tables)

# 3. 核心业务链路：候选菜谱 → 待采购代入 → 移除回退（COOK 一致）
from fastapi.testclient import TestClient  # noqa: E402

c = TestClient(app.main.app)

# 3.1 建一道菜谱，需 2 份「番茄」+1 份「鸡蛋」
r = c.post("/recipes", json={
    "source": "my", "name": "番茄炒蛋", "em": "🍅",
    "ing": [{"name": "番茄", "qty": 2, "unit": "个"}, {"name": "鸡蛋", "qty": 1, "unit": "个"}],
})
rid = r.json()["id"]

# 3.2 冰箱在库只有 1 个番茄
c.post("/fridge/in_stock", json={"name": "番茄", "qty": 1, "unit": "个", "days": 7})
c.post("/fridge/in_stock", json={"name": "鸡蛋", "qty": 1, "unit": "个", "days": 7})

# 3.3 加入候选 → 应代入 1 个番茄、0 个鸡蛋
cid = c.post("/candidates", json={"kind": "recipe", "ref_id": rid}).json()["id"]
purchase = {p["name"]: p["qty"] for p in c.get("/fridge/purchase").json()}
print("[3] 加入候选后代购:", purchase)
assert purchase.get("番茄") == 1, "番茄应代入 1"
assert "鸡蛋" not in purchase, "鸡蛋充足不应代入"

# 3.4 移除候选 → 回退 1 个番茄
c.delete(f"/candidates/{cid}")
purchase2 = c.get("/fridge/purchase").json()
print("[4] 移除候选后回退:", purchase2)
assert purchase2 == [], "回退后待采购应变空"

# 3.5 计时
c.post(f"/candidates", json={"kind": "recipe", "ref_id": rid})
cid2 = [x["id"] for x in c.get("/candidates").json() if x["ref_id"] == rid][0]
c.post(f"/candidates/{cid2}/timer/start")
t = c.get(f"/candidates/{cid2}/timer").json()
print("[5] 计时状态:", t)
assert t["running"] is True

# 3.6 配置表
c.put("/configs/expiry_threshold_days", json={"value": "5"})
cfg = {x["key"]: x["value"] for x in c.get("/configs").json()}
print("[6] 配置表:", cfg)

# 3.7 厨房技巧审核闭环
t1 = c.post("/tips", json={"title": "蒸鱼诀窍", "content": "冷水下锅", "author": "小明", "pub": True}).json()
assert c.get("/tips", params={"viewer": "小红"}).json() == [], "未审通过不应被他人可见"
c.post(f"/tips/{t1['id']}/approve")
vis = c.get("/tips", params={"viewer": "小红"}).json()
print("[7] 审核后他人可见数:", len(vis))
assert len(vis) == 1

print("\n全部断言通过 ✅")