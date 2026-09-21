# -*- coding: utf-8 -*-
"""
数据库访问层（SQLite，轻量起步，后续可平滑迁移到 PostgreSQL）。

设计要点（对齐 DESIGN.md）：
- 派生数据一律实时计算，不落冗余存储（如待采购、饮品统计、临期状态均由原始数据现算）。
- 配置文件 key/value 管理环境参数（审核开关、临期阈值等），不散落在代码里。
- 每个请求一个独立连接，事务提交由依赖收尾统一处理；出错即回滚，保证 COOK 一致性。
- JSON 字段（tags / ing / steps / subs / must / arrive 等）以 TEXT 存储，出入自动序列化。
"""
import json
import sqlite3
from pathlib import Path

# 数据库文件放在 backend 目录下
DB_PATH = Path(__file__).resolve().parent.parent / "eatwhat.db"

# ---------------------------------------------------------------------------
# Schema（DDL）：建表 + 配置种子 + 默认管理员
# ---------------------------------------------------------------------------
SCHEMA = """
-- 用户（MVP 仅做最简，后续可接真实登录）
CREATE TABLE IF NOT EXISTS users(
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT NOT NULL,
    role    TEXT NOT NULL DEFAULT 'user'   -- user | admin
);

-- 配置表：环境参数统一走这里，避免散落代码
CREATE TABLE IF NOT EXISTS configs(
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL DEFAULT ''
);

-- 菜谱：source=my 我的菜谱（可编辑）；source=admin 参考菜谱（只读）
CREATE TABLE IF NOT EXISTS recipes(
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    source  TEXT NOT NULL DEFAULT 'my',    -- my | admin
    name    TEXT NOT NULL,
    em      TEXT NOT NULL DEFAULT '🍽',
    cover   TEXT NOT NULL DEFAULT '',     -- 选用的封面 id（来自 covers 表，空=默认轮换）
    time    INTEGER NOT NULL DEFAULT 0,    -- 用时（分钟）
    diff    TEXT NOT NULL DEFAULT '简单',   -- 难度
    tags    TEXT NOT NULL DEFAULT '[]',    -- JSON 数组：口味/标签
    ing     TEXT NOT NULL DEFAULT '[]',    -- JSON 数组：[{name,qty,unit}]
    steps   TEXT NOT NULL DEFAULT '[]'     -- JSON 数组：步骤文本
);

-- 食材库：菜谱选食材的独立维护来源（与冰箱库存解耦）
-- 设计：菜谱所需食材是「需求」，冰箱在库/待采购是「库存」；需求不从库存派生，
-- 故单独建一套可维护的食材池，菜谱编辑从其选择，库存只负责当前拥有/待采购。
CREATE TABLE IF NOT EXISTS ingredients(
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    cat  TEXT NOT NULL DEFAULT '其他'   -- 食材大类名（挂在 categories.name 下）
);

-- 食材大类：独立实体，支持 增/删/改名/换图标/排序
-- name 供各食物表以名字关联（改名需级联更新 ingredients / fridge_items.cat）
CREATE TABLE IF NOT EXISTS categories(
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    icon TEXT NOT NULL DEFAULT '🥗',
    sort INTEGER NOT NULL DEFAULT 0      -- 展示顺序
);

-- 封面图库：管理员维护的固定封面（emoji + 渐变主题），菜谱编辑时从中点选。
-- 菜谱.cover 存封面 id；渲染时取其 emoji 作菜示图、grad 作背景，空则回退默认轮换。
CREATE TABLE IF NOT EXISTS covers(
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    emoji TEXT NOT NULL DEFAULT '🍽',
    name  TEXT NOT NULL DEFAULT '',        -- 封面色调名（可选，便于维护识别）
    grad  TEXT NOT NULL DEFAULT 'linear-gradient(135deg,#4b3fe3,#8b5cf6)',  -- CSS 渐变背景
    sort  INTEGER NOT NULL DEFAULT 0       -- 展示顺序
);

-- 冰箱-在库：单条食材，状态（充足/临期）实时现算
CREATE TABLE IF NOT EXISTS fridge_items(
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    name   TEXT NOT NULL,
    cat    TEXT NOT NULL DEFAULT '其他',    -- 食材大类
    qty    REAL NOT NULL DEFAULT 0,        -- 存量
    unit   TEXT NOT NULL DEFAULT '份',
    store  TEXT NOT NULL DEFAULT '',       -- 存放位置（可选）
    buy    TEXT NOT NULL DEFAULT '',       -- 采购日期 YYYY-MM-DD
    days   INTEGER NOT NULL DEFAULT 7       -- 保质期（天）
);

-- 冰箱-待采购：由在库不足代号入，也可手工维护
CREATE TABLE IF NOT EXISTS purchase(
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name  TEXT NOT NULL,
    qty   REAL NOT NULL DEFAULT 0,
    unit  TEXT NOT NULL DEFAULT '份',
    UNIQUE(name, unit)
);

-- 候选收件箱（吃这些）：kind=recipe 菜谱 / shop 餐厅
-- subs：JSON {name: 数量}，记录该候选代号入待采购的量，移除时按量回退，保证 COOK 一致
CREATE TABLE IF NOT EXISTS eat_inbox(
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    kind     TEXT NOT NULL,                -- recipe | shop
    ref_id   INTEGER,                      -- 关联菜谱/餐厅 id（可为空）
    name     TEXT NOT NULL,
    em       TEXT NOT NULL DEFAULT '🍽',
    subs     TEXT NOT NULL DEFAULT '{}',   -- 代号入待采购映射
    added_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- 多道并行计时：tracks 挂在候选上
CREATE TABLE IF NOT EXISTS tracks(
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    inbox_id INTEGER NOT NULL UNIQUE,      -- 一个候选最多一个计时
    started  TEXT,                         -- 开始时间（ISO）
    paused   INTEGER NOT NULL DEFAULT 0,   -- 已暂停累计秒
    running  INTEGER NOT NULL DEFAULT 1    -- 1 运行中 0 已暂停
);

-- 餐厅收藏
CREATE TABLE IF NOT EXISTS shops(
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    name      TEXT NOT NULL,
    type      TEXT NOT NULL DEFAULT '中餐',
    price     TEXT NOT NULL DEFAULT '',
    star      REAL NOT NULL DEFAULT 0,
    must      TEXT NOT NULL DEFAULT '[]',  -- JSON：招牌菜
    note      TEXT NOT NULL DEFAULT '',
    arr_min   INTEGER NOT NULL DEFAULT 0,  -- 到达耗时（分钟）
    transport TEXT NOT NULL DEFAULT '步行', -- 交通工具
    tags      TEXT NOT NULL DEFAULT '[]'   -- JSON：口味标签
);

-- 干饭成员（用餐人）：每人维护口味偏好
CREATE TABLE IF NOT EXISTS diners(
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '[]'        -- JSON：口味/忌口/辣度
);

-- 厨房技巧（内容社区 + 审核闭环）
CREATE TABLE IF NOT EXISTS tips(
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    title   TEXT NOT NULL,
    content TEXT NOT NULL,
    cat     TEXT NOT NULL DEFAULT '其他',
    author  TEXT NOT NULL,                 -- 作者（MVP 用名字标识）
    pub     INTEGER NOT NULL DEFAULT 1,    -- 1 公开 0 仅自己
    status  TEXT NOT NULL DEFAULT 'pending',-- pending | approved | rejected
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at TEXT
);

-- 饮食记录（唯一 id，可编辑/删除）
CREATE TABLE IF NOT EXISTS records(
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,                    -- YYYY-MM-DD
    name TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'cook'      -- cook 自己做 | out 餐厅 | delivery 外卖
);

-- 体重记录（含体脂）
CREATE TABLE IF NOT EXISTS weights(
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    date      TEXT NOT NULL,
    weight    REAL NOT NULL,
    body_fat  REAL
);
"""


def get_conn() -> sqlite3.Connection:
    """新建一个数据库连接（每请求一个），已配置 Row 工厂与外键约束。"""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """初始化数据库：建表 + 写默认配置与管理员。可重复调用（幂等）。"""
    conn = get_conn()
    try:
        conn.executescript(SCHEMA)
        # 迁移：老库 recipes 表缺 cover 列（新库建表时已带，这里幂等补列）
        _cols = {r[1] for r in conn.execute("PRAGMA table_info(recipes)").fetchall()}
        if "cover" not in _cols:
            conn.execute("ALTER TABLE recipes ADD COLUMN cover TEXT NOT NULL DEFAULT ''")
        # 默认配置：审核开关（1 开 0 关）、临期阈值天数
        conn.execute("INSERT OR IGNORE INTO configs(key,value) VALUES('audit_enabled','1')")
        conn.execute("INSERT OR IGNORE INTO configs(key,value) VALUES('expiry_threshold_days','3')")
        # 默认管理员
        conn.execute("INSERT OR IGNORE INTO users(id,name,role) VALUES(1,'管理员','admin')")
        # 食材大类默认种子：仅当表为空时写入（避免把用户删除/改名的大类复活）
        if conn.execute("SELECT 1 FROM categories LIMIT 1").fetchone() is None:
            _DEFAULT_CATS = [
                ("蔬菜", "🥬"), ("水果", "🍎"), ("肉类", "🥩"), ("水产", "🦐"),
                ("菌菇", "🍄"), ("蛋奶", "🥚"), ("主食", "🍚"), ("调料", "🧂"), ("其他", "🥗"),
            ]
            for i, (cname, icon) in enumerate(_DEFAULT_CATS):
                conn.execute(
                    "INSERT OR IGNORE INTO categories(name,icon,sort) VALUES(?,?,?)",
                    (cname, icon, i),
                )
        # 封面库默认种子：仅空表时写入（管理员可增删改，不清空用户改动）
        if conn.execute("SELECT 1 FROM covers LIMIT 1").fetchone() is None:
            _DEFAULT_COVERS = [
                # (emoji, 色调名, 渐变) —— 与前端封面选择器一致，供管理员维护默认底稿
                ("🍽", "紫罗兰", "linear-gradient(135deg,#4b3fe3,#8b5cf6)"),
                ("🥩", "橙红", "linear-gradient(135deg,#ec4899,#f97316)"),
                ("🦐", "海蓝", "linear-gradient(135deg,#06b6d4,#3b82f6)"),
                ("🥬", "青绿", "linear-gradient(135deg,#10b981,#a3e635)"),
                ("🍳", "粉紫", "linear-gradient(135deg,#8b5cf6,#d946ef)"),
                ("🌶", "火橙", "linear-gradient(135deg,#f59e0b,#ef4444)"),
                ("🍚", "暖米", "linear-gradient(135deg,#f9a825,#ef6c00)"),
                ("🥗", "薄荷", "linear-gradient(135deg,#34d399,#22c55e)"),
                ("🍎", "玫红", "linear-gradient(135deg,#f43f5e,#ef4444)"),
                ("🍜", "棕面", "linear-gradient(135deg,#a16207,#ca8a04)"),
                ("🍕", "意式", "linear-gradient(135deg,#e11d48,#f97316)"),
                ("🧊", "冷蓝", "linear-gradient(135deg,#38bdf8,#6366f1)"),
            ]
            for i, (emo, nm, grad) in enumerate(_DEFAULT_COVERS):
                conn.execute(
                    "INSERT OR IGNORE INTO covers(emoji,name,grad,sort) VALUES(?,?,?,?)",
                    (emo, nm, grad, i),
                )
        # 食材库种子（幂等）：从现有在库 / 待采购 / 菜谱食材去重收录，并补几个常用食材，
        # 保证「菜谱选食材」首个下拉非空，且旧数据里的食材名仍可选。
        for name, cat in conn.execute("SELECT name, cat FROM fridge_items"):
            conn.execute("INSERT OR IGNORE INTO ingredients(name,cat) VALUES(?,?)", (name, cat))
        for (name,) in conn.execute("SELECT name FROM purchase"):
            conn.execute("INSERT OR IGNORE INTO ingredients(name,cat) VALUES(?,?)", (name, "其他"))
        for row in conn.execute("SELECT ing FROM recipes WHERE ing!='[]'"):
            for it in json.loads(row["ing"]):
                if it.get("name"):
                    conn.execute(
                        "INSERT OR IGNORE INTO ingredients(name,cat) VALUES(?,?)",
                        (it["name"], "其他"),
                    )
        for nm, ct in (("鸡蛋", "蛋奶"), ("番茄", "蔬菜"), ("米饭", "主食"), ("青菜", "蔬菜"),
                       ("五花肉", "肉类"), ("虾仁", "水产")):
            conn.execute("INSERT OR IGNORE INTO ingredients(name,cat) VALUES(?,?)", (nm, ct))
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# FastAPI 依赖：每请求一个连接，成功自动提交，异常自动回滚
# ---------------------------------------------------------------------------
def get_db():
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# JSON 字段序列化助手
# ---------------------------------------------------------------------------
def jdump(v) -> str:
    return json.dumps(v, ensure_ascii=False)


def jload(s, default=None):
    if s is None or s == "":
        return default if default is not None else []
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return default if default is not None else []


def row_to_dict(row: sqlite3.Row) -> dict:
    """把 sqlite3.Row 转 dict，并自动把 JSON 字段反序列化为 Python 对象。"""
    if row is None:
        return None
    d = dict(row)
    for col in ("tags", "ing", "steps", "must", "arrive", "subs"):
        if col in d:
            d[col] = jload(d[col])
    return d