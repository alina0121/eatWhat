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
import re
import sqlite3
from pathlib import Path

# 数据库文件放在 backend 目录下
DB_PATH = Path(__file__).resolve().parent.parent / "eatwhat.db"

# ---------------------------------------------------------------------------
# Schema（DDL）：建表 + 配置种子 + 默认管理员
# ---------------------------------------------------------------------------
SCHEMA = """
-- 用户（微信登录 + JWT 鉴权，后端用 openid 唯一标识）
CREATE TABLE IF NOT EXISTS users(
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL DEFAULT '',                 -- 显示名（管理端同名校验、老链路读取仍用）
    openid      TEXT UNIQUE,                              -- 微信 openid（唯一）
    unionid     TEXT NOT NULL DEFAULT '',                 -- 微信 unionid（同主体多 app 共享）
    email       TEXT NOT NULL DEFAULT '',                 -- 绑定邮箱（唯一，空串=未绑定）
    nickname    TEXT NOT NULL DEFAULT '',                 -- 昵称（新版 chooseAvatar + nickname input）
    avatar      TEXT NOT NULL DEFAULT '',                 -- 头像 URL（临时链接，微信返回的）
    signature   TEXT NOT NULL DEFAULT '',                 -- 个性签名（空=前端显示默认「好好吃饭好好生活」）
    role        TEXT NOT NULL DEFAULT 'user',             -- user | admin
    created_at  INTEGER NOT NULL DEFAULT 0,               -- 注册时间戳
    last_seen   INTEGER NOT NULL DEFAULT 0                -- 最近活跃时间戳
);

-- 邮箱验证码（临时表，发码/校验用，用后标记 used=1，过期自动忽略）
CREATE TABLE IF NOT EXISTS email_otps(
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    email      TEXT NOT NULL,
    code       TEXT NOT NULL,                              -- 6 位数字
    purpose    TEXT NOT NULL DEFAULT 'login',              -- login | bind | reset
    expired_at INTEGER NOT NULL,                           -- 时间戳（秒）
    used       INTEGER NOT NULL DEFAULT 0,                 -- 0 未用 / 1 已用
    created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_otp_email ON email_otps(email);

-- 配置表：环境参数统一走这里，避免散落代码
CREATE TABLE IF NOT EXISTS configs(
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL DEFAULT ''
);

-- 菜谱：source=my 我的菜谱（可编辑）；source=admin 参考菜谱（只读）
CREATE TABLE IF NOT EXISTS recipes(
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL DEFAULT 1,    -- 所属用户；source=admin 的参考菜谱是公共内容，不按此列过滤
    source  TEXT NOT NULL DEFAULT 'my',    -- my | admin
    name    TEXT NOT NULL,
    em      TEXT NOT NULL DEFAULT '🍽',
    cover   TEXT NOT NULL DEFAULT '',     -- 封面渐变（纯 CSS linear-gradient 字符串，或空=留白），emoji 由 recipes.em 字段独立负责
    time    INTEGER NOT NULL DEFAULT 0,    -- 用时（分钟）
    diff    TEXT NOT NULL DEFAULT '简单',   -- 难度
    tags    TEXT NOT NULL DEFAULT '[]',    -- JSON 数组：口味/标签
    ing     TEXT NOT NULL DEFAULT '[]',    -- JSON 数组：[{name,qty,unit}]
    steps   TEXT NOT NULL DEFAULT '[]',    -- JSON 数组：步骤文本
    star    INTEGER NOT NULL DEFAULT 0     -- 喜好星级 0-5（列表按其倒序展示）
);

-- 食材库：双层模型——公共（scope=public）+ 用户私有补录（scope=user）
-- list 默认返回「公共 + 用户自己补录」，同名公共优先（用户不能补公共已有的）；
-- admin=true 管理端只看 public 层；user 端 create 默认 scope='user'。
CREATE TABLE IF NOT EXISTS ingredients(
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL DEFAULT 1,      -- 所属用户（scope=public 时为 1）
    scope   TEXT NOT NULL DEFAULT 'user',    -- public | user
    name    TEXT NOT NULL,
    cat     TEXT NOT NULL DEFAULT '其他',    -- 食材大类名
    icon    TEXT NOT NULL DEFAULT ''          -- 独立 emoji 图标（空=列表渲染回退用大类 icon）
);

-- 食材大类：同 ingredients 双层模型——公共大类 + 用户私有补录
CREATE TABLE IF NOT EXISTS categories(
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL DEFAULT 1,
    scope   TEXT NOT NULL DEFAULT 'user',    -- public | user
    name    TEXT NOT NULL,
    icon    TEXT NOT NULL DEFAULT '🥗',
    sort    INTEGER NOT NULL DEFAULT 0
);

-- 冰箱-在库：单条食材，状态（充足/临期）实时现算；按 user_id 隔离
CREATE TABLE IF NOT EXISTS fridge_items(
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL DEFAULT 1,      -- 所属用户
    name    TEXT NOT NULL,
    cat     TEXT NOT NULL DEFAULT '其他',    -- 食材大类
    qty     REAL NOT NULL DEFAULT 0,         -- 存量
    unit    TEXT NOT NULL DEFAULT '份',
    store   TEXT NOT NULL DEFAULT '',        -- 存放位置（可选）
    buy     TEXT NOT NULL DEFAULT '',        -- 采购日期 YYYY-MM-DD
    days    INTEGER NOT NULL DEFAULT 7        -- 保质期（天）
);

-- 冰箱-待采购：按 user_id 隔离；唯一键变为 (user_id, name, unit)
CREATE TABLE IF NOT EXISTS purchase(
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL DEFAULT 1,      -- 所属用户
    name    TEXT NOT NULL,
    qty     REAL NOT NULL DEFAULT 0,
    unit    TEXT NOT NULL DEFAULT '份',
    UNIQUE(user_id, name, unit)
);

-- 候选收件箱（吃这些）：kind=recipe 菜谱 / shop 餐厅
-- subs：JSON {name: 数量}，记录该候选代号入待采购的量，移除时按量回退，保证 COOK 一致
-- family_id：0=个人池；>0=家庭空间共享池（成员可见可操作）
-- creator_id：实际加入人。缺货代入/回退始终记在加者的 fridge/purchase 上（家庭池里 B 删 A 加的 → 回退 A 的待采购）
CREATE TABLE IF NOT EXISTS eat_inbox(
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL DEFAULT 1,   -- 所属用户：候选/计时都属于创建它的那个人
    kind       TEXT NOT NULL,                -- recipe | shop
    ref_id     INTEGER,                      -- 关联菜谱/餐厅 id（可为空）
    name       TEXT NOT NULL,
    em         TEXT NOT NULL DEFAULT '🍽',
    subs       TEXT NOT NULL DEFAULT '{}',   -- 代号入待采购映射
    family_id  INTEGER NOT NULL DEFAULT 0,   -- 0=个人池；>0=家庭空间共享池
    creator_id INTEGER NOT NULL DEFAULT 0,   -- 实际加入人（记账用；老数据为 0，回退 user_id）
    added_at   TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- 多道并行计时：tracks 挂在候选上
CREATE TABLE IF NOT EXISTS tracks(
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    inbox_id INTEGER NOT NULL UNIQUE,      -- 一个候选最多一个计时
    started  TEXT,                         -- 开始时间（ISO）
    paused   INTEGER NOT NULL DEFAULT 0,   -- 已暂停累计秒
    running  INTEGER NOT NULL DEFAULT 1    -- 1 运行中 0 已暂停
);

-- 家庭空间：共享「吃这些」候选池；6 位邀请码加入（对齐下厨房家庭库交互）
CREATE TABLE IF NOT EXISTS families(
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    code       TEXT UNIQUE NOT NULL,             -- 6 位大写字母数字邀请码（去掉易混淆 0O1I）
    name       TEXT NOT NULL,                    -- 家庭名
    owner_id   INTEGER NOT NULL,                 -- 创建者（退出即解散）
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- 家庭成员：一人一家庭（user_id 唯一约束保证；退出后可再加入别的家庭）
CREATE TABLE IF NOT EXISTS family_members(
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    family_id INTEGER NOT NULL,
    user_id   INTEGER NOT NULL UNIQUE,
    joined_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- 餐厅收藏
CREATE TABLE IF NOT EXISTS shops(
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id   INTEGER NOT NULL DEFAULT 1,  -- 所属用户：餐厅收藏按人隔离
    name      TEXT NOT NULL,
    type      TEXT NOT NULL DEFAULT '中餐',
    price     TEXT NOT NULL DEFAULT '',
    star      REAL NOT NULL DEFAULT 0,
    must      TEXT NOT NULL DEFAULT '[]',  -- JSON：招牌菜
    note      TEXT NOT NULL DEFAULT '',
    arr_min   INTEGER NOT NULL DEFAULT 0,  -- 到达耗时（分钟）
    transport TEXT NOT NULL DEFAULT '步行', -- 交通工具
    tags      TEXT NOT NULL DEFAULT '[]',   -- JSON：口味标签
    icon      TEXT NOT NULL DEFAULT '🏪'   -- emoji 图标
);

-- 口味标签池：每个用户独立维护自己的标签，菜谱/推荐筛选都从这里取
CREATE TABLE IF NOT EXISTS taste_tags(
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name    TEXT NOT NULL,
    sort    INTEGER NOT NULL DEFAULT 0,
    UNIQUE(user_id, name)
);

-- 厨房技巧（内容社区 + 审核闭环）
CREATE TABLE IF NOT EXISTS tips(
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL DEFAULT 1,    -- 所属用户：决定「只能改自己的」，author 仅用于展示
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
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL DEFAULT 1,   -- 所属用户：饮食记录按人隔离
    date    TEXT NOT NULL,                -- YYYY-MM-DD
    name    TEXT NOT NULL,
    type    TEXT NOT NULL DEFAULT 'cook'      -- cook 自己做 | out 餐厅 | delivery 外卖
);

-- 会员开通记录（不挂 users 表：init_db 对列不一致的表整删重建，动 users 会清空线上用户数据）
CREATE TABLE IF NOT EXISTS vip_members(
    user_id    INTEGER PRIMARY KEY,               -- 一人一行
    expires_at INTEGER NOT NULL DEFAULT 0,        -- 到期时间戳（秒）；> now 即会员
    updated_at INTEGER NOT NULL DEFAULT 0
);

-- 会员订单（微信虚拟支付；mock 模式下单即标记已付，联调用）
CREATE TABLE IF NOT EXISTS orders(
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL,
    out_trade_no  TEXT UNIQUE NOT NULL,           -- 商户单号
    plan_id       TEXT NOT NULL,                  -- 对应 vip_plans 里的键（monthly/yearly）
    price_fen     INTEGER NOT NULL,               -- 下单时快照（分），改配置不影响历史订单
    plan_days     INTEGER NOT NULL DEFAULT 0,     -- 下单时快照：开通天数
    status        TEXT NOT NULL DEFAULT 'pending',-- pending | paid | refunded
    credited      INTEGER NOT NULL DEFAULT 0,     -- 会员时长是否已发放（防对账重放时重复续期）
    env           INTEGER NOT NULL DEFAULT 0,     -- 0 安卓/其他 / 1 iOS（对账分渠道费率）
    wx_transaction_id TEXT NOT NULL DEFAULT '',   -- 微信侧单号
    created_at    INTEGER NOT NULL,
    paid_at       INTEGER
);
CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id);

-- 体重记录（含体脂）
CREATE TABLE IF NOT EXISTS weights(
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id   INTEGER NOT NULL DEFAULT 1,  -- 所属用户：体重记录按人隔离
    date      TEXT NOT NULL,
    weight    REAL NOT NULL,
    body_fat  REAL
);
"""


def _schema_columns() -> dict:
    """从 SCHEMA 解析每张表应有的列名集合：{表名: {列名, ...}}。"""
    tables = {}
    for m in re.finditer(r"CREATE TABLE IF NOT EXISTS\s+(\w+)\s*\((.*?)\);", SCHEMA, re.S):
        cols = set()
        for line in m.group(2).splitlines():
            line = line.strip().rstrip(",")
            if line and line.split()[0].isidentifier():
                cols.add(line.split()[0])
        tables[m.group(1)] = cols
    return tables


# 增量列迁移：老库启动时用 ALTER TABLE 补新列（必须在整表重建判断**之前**执行）。
# 否则 SCHEMA 给已有表加列后，下面的列比对会把老表判为「列不一致」而 DROP 重建，
# 直接清掉用户数据。格式：{表名: [(列名, 列定义), ...]}
_MIGRATIONS = {
    "eat_inbox": [
        ("family_id", "INTEGER NOT NULL DEFAULT 0"),
        ("creator_id", "INTEGER NOT NULL DEFAULT 0"),
    ],
    "users": [
        ("signature", "TEXT NOT NULL DEFAULT ''"),
    ],
}


def get_conn() -> sqlite3.Connection:
    """新建一个数据库连接（每请求一个），已配置 Row 工厂与外键约束。"""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """初始化数据库：建表 + 写默认配置与管理员。可重复调用（幂等）。

    表结构一律以 SCHEMA 为准：现有表与 SCHEMA 列不一致（缺列或多列）
    就整表删除重建，不做历史数据迁移——结构不适配的旧数据直接丢弃。
    """
    conn = get_conn()
    try:
        expected = _schema_columns()
        existing = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        # 增量迁移先行：给老表补新增列，让下面的列比对通过，避免老表被 DROP 重建清数据
        for tbl, cols in _MIGRATIONS.items():
            if tbl in existing:
                actual = {r[1] for r in conn.execute(f"PRAGMA table_info({tbl})").fetchall()}
                for col_name, col_def in cols:
                    if col_name not in actual:
                        conn.execute(f"ALTER TABLE {tbl} ADD COLUMN {col_name} {col_def}")
        # 下线功能残留清理：diners（干饭成员）已移除，老库启动时直接删表（幂等）
        conn.execute("DROP TABLE IF EXISTS diners")
        for tbl, cols in expected.items():
            if tbl in existing:
                actual = {r[1] for r in conn.execute(f"PRAGMA table_info({tbl})").fetchall()}
                if actual != cols:
                    conn.execute(f"DROP TABLE {tbl}")
        conn.executescript(SCHEMA)
        # 默认配置：审核开关（1 开 0 关）、临期阈值天数
        conn.execute("INSERT OR IGNORE INTO configs(key,value) VALUES('audit_enabled','1')")
        conn.execute("INSERT OR IGNORE INTO configs(key,value) VALUES('expiry_threshold_days','3')")
        # 管理端登录口令：仅门控管理台，不影响移动端（MVP 语义，上线可改库）
        conn.execute("INSERT OR IGNORE INTO configs(key,value) VALUES('admin_passcode','123456')")
        # 食材图标池：食材独立 emoji 候选（逗号分隔），管理端维护，食材新增/编辑时从这里选
        conn.execute("INSERT OR IGNORE INTO configs(key,value) VALUES('ingredient_icon_pool','🥬,🥕,🥦,🥒,🌽,🍅,🥑,🍎,🍌,🍇,🍊,🍓,🍑,🥭,🥩,🥚,🥓,🍗,🦐,🦞,🦀,🐟,🍄,🧀,🥛,🍚,🍞,🥜,🌰,🫘,🧂,🌶,🫚,🧄,🍠,🥔,🍆,🥥,🍋,🫐')")
        # 大类图标池：emoji 候选（逗号分隔），管理端维护，前端从配置读
        conn.execute("INSERT OR IGNORE INTO configs(key,value) VALUES('cat_icon_pool','🥬,🍎,🥩,🦐,🍄,🥚,🍚,🧂,🥗,🌰,🫘,🧀,🍞,🍜,🥛,🌶,🥜,🍇')")
        # 菜谱图标池：菜谱列表/详情的 emoji 候选（逗号分隔），管理端维护
        conn.execute("INSERT OR IGNORE INTO configs(key,value) VALUES('recipe_emoji_pool','🍽,🍲,🍜,🍕,🍔,🍟,🥗,🥘,🍛,🍣,🍱,🥙,🌮,🍤,🍢,🥟,🍙,🍝,🥗,🍳')")
        # 餐厅图标池：餐厅收藏 emoji 候选（逗号分隔），管理端维护
        conn.execute("INSERT OR IGNORE INTO configs(key,value) VALUES('shop_icon_pool','🏪,🍜,🍲,🍣,🏮,🥟,🍢,🌮,🍕,🥘,🍱,🍛,🍗,🥙,🏠,🏢,🏖️,🏔️')")
        # 微信内容安全检测：小程序提审要求 UGC 必须送检（见 app/wxsec.py）
        # 默认关闭 → 配好 mp_appid/mp_secret 后把 wx_sec_enabled 置 1 生效，本地/H5 不受影响
        conn.execute("INSERT OR IGNORE INTO configs(key,value) VALUES('wx_sec_enabled','0')")
        conn.execute("INSERT OR IGNORE INTO configs(key,value) VALUES('mp_appid','')")
        conn.execute("INSERT OR IGNORE INTO configs(key,value) VALUES('mp_secret','')")
        # JWT 签名密钥（务必改！默认值仅开发期占位）
        conn.execute("INSERT OR IGNORE INTO configs(key,value) VALUES('jwt_secret','eatwhat-change-me-1234567890')")
        # SMTP 邮箱服务（管理员维护，QQ/163 邮箱都支持，端口 465 SSL / 587 TLS）
        # 没配 → 发验证码降级为后端日志打印，开发期可用
        conn.execute("INSERT OR IGNORE INTO configs(key,value) VALUES('smtp_host','')")
        conn.execute("INSERT OR IGNORE INTO configs(key,value) VALUES('smtp_port','465')")
        conn.execute("INSERT OR IGNORE INTO configs(key,value) VALUES('smtp_user','')")
        conn.execute("INSERT OR IGNORE INTO configs(key,value) VALUES('smtp_pass','')")
        conn.execute("INSERT OR IGNORE INTO configs(key,value) VALUES('smtp_from','吃啥好呀')")
        # 验证码有效期（分钟）：默认给 30，避免 QQ/163 投递延迟时「刚收到就已经过期」
        conn.execute("INSERT OR IGNORE INTO configs(key,value) VALUES('otp_expire_min','30')")
        # 会员体系（管理后台「会员与收款」区维护，改完即生效）
        # vip_enabled：总开关，'0' 时一切限制解除（额度/回看都不生效）
        conn.execute("INSERT OR IGNORE INTO configs(key,value) VALUES('vip_enabled','0')")
        # vip_pay_mode：mock=沙箱（下单即开通，本地/联调用）；wxpay=微信虚拟支付（需在管理后台配 offer_id/pay_key 并完成虚拟支付签约）
        conn.execute("INSERT OR IGNORE INTO configs(key,value) VALUES('vip_pay_mode','mock')")
        # free_quota：免费额度（-1 或缺省 = 该维度不限）
        conn.execute("INSERT OR IGNORE INTO configs(key,value) VALUES('free_quota'," + repr(
            '{"recipes":20,"ingredients":50,"shops":10,"tips":10,'
            '"records_view_days":60,"weights_view_days":90}'
        ) + ")")
        # vip_plans：套餐定义（price_fen 单位为分；days 为开通天数）
        conn.execute("INSERT OR IGNORE INTO configs(key,value) VALUES('vip_plans'," + repr(
            '{"monthly":{"name":"连续包月","price_fen":600,"days":30},'
            '"yearly":{"name":"年卡","price_fen":4500,"days":365,"hot":1}}'
        ) + ")")
        # 微信虚拟支付商户参数（开通后在小程序后台「虚拟支付-基础配置」里拿）
        conn.execute("INSERT OR IGNORE INTO configs(key,value) VALUES('wxpay_offer_id','')")
        conn.execute("INSERT OR IGNORE INTO configs(key,value) VALUES('wxpay_pay_key','')")
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
        # 封面渐变预设池：| 分隔，每个是一个 CSS linear-gradient，管理端维护，菜谱编辑时直接选
        conn.execute("INSERT OR IGNORE INTO configs(key,value) VALUES('cover_grad_pool'," + repr(
            "linear-gradient(135deg,#4b3fe3,#8b5cf6)|"
            "linear-gradient(135deg,#ec4899,#f97316)|"
            "linear-gradient(135deg,#06b6d4,#3b82f6)|"
            "linear-gradient(135deg,#10b981,#a3e635)|"
            "linear-gradient(135deg,#8b5cf6,#d946ef)|"
            "linear-gradient(135deg,#f59e0b,#ef4444)|"
            "linear-gradient(135deg,#f9a825,#ef6c00)|"
            "linear-gradient(135deg,#34d399,#22c55e)|"
            "linear-gradient(135deg,#f43f5e,#ef4444)|"
            "linear-gradient(135deg,#a16207,#ca8a04)|"
            "linear-gradient(135deg,#e11d48,#f97316)|"
            "linear-gradient(135deg,#38bdf8,#6366f1)"
        ) + ")")
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
        # 默认口味标签：给 user_id=1 种 6 个常用
        default_tags = ['麻辣', '家常', '清淡', '快手', '下饭', '宴客']
        for i, t in enumerate(default_tags):
            conn.execute("INSERT OR IGNORE INTO taste_tags(user_id,name,sort) VALUES(1,?,?)", (t, i))
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