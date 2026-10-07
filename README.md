# 吃啥好呀（eatWhat）

一个帮你解决「今天吃啥」的轻量级全栈应用。把菜谱、冰箱库存、餐厅收藏、干饭记录聚到一起，
加菜谱候选自动代入缺货采购、并行厨房计时、多人口味筛选，再配上管理员维护的内容社区。

> **MVP 定位**：轻量起步。后端 FastAPI + SQLite 单文件数据库，前端 uni-app（Vue3）一套代码
> 可跑 **H5 / 微信小程序 / App**。当前主要打磨 **H5（Web）** 端。

---

## ✨ 功能总览

| 模块 | 说明 |
| --- | --- |
| 🍽 吃这些（候选） | 把菜谱/餐厅加入今日候选收件箱，一键**缺货代入待采购**；移除时**按量精确回退**（会计一致性由 `subs` 保证） |
| ⏱ 厨房计时 | 候选可**多道并行**计时：开始 / 暂停 / 继续 / 取消，实时走表，适合边做题边做菜的厨房场景 |
| 📖 菜谱 | 自己的菜谱 + 管理员录入的**参考菜谱**；支持难度、耗时、口味标签、所需食材、分步教程；封面从**封面图库**点选 |
| 🧊 冰箱 | **在库**（充足 / 临期 / 已过期 + 剩余天数，按采购日期+保质期**实时计算**）+ **待采购**两套库存 |
| 🥬 食材库 & 大类 | 菜谱选食材的独立来源，与冰箱库存解耦；大类可增删改名换图标排序 |
| 🏪 餐厅 | 收藏餐厅：类型、人均、星级、招牌菜、到达耗时与交通方式 |
| 👥 干饭成员 | 每位成员维护口味偏好（⚠️ 快捷键 `Ctrl+K` 输入「干饭成员」）、实现**按口味筛选** |
| 📝 干饭记录 | 按日记录自己做 / 餐厅 / 外卖；月历视图 + 月切换 |
| ⚖️ 体重记录 | 记录体重与体脂 |
| 👨🍳 厨房技巧 | 内容社区：所有人可新增/公开或私藏，**管理员审核**闭环（待审核 / 已公开 / 未通过） |
| 🖥️ PC 管理端 | 桌面宽屏下的管理台：技巧审核 / 参考菜谱 / 封面图库 / 食材库&大类 / 餐厅 / 系统配置 |
| ⚙️ 系统配置 | 审核开关、临期阈值等**配置表驱动**，修改立即生效 |

---

## 🧱 技术栈

**后端**（`backend/`）
- Python · FastAPI · uvicorn
- SQLite（单文件 `eatwhat.db`，轻量起步；每请求独立连接，事务提交收尾统一处理）
- Pydantic 2.x

**前端**（`frontend/`）
- uni-app（Vue3 + Vite + Sass），多端编译（H5 / 微信小程序 / App）
- 自定义底部导航、全自定义页面导航条（`navigationStyle: custom`）
- 页面与逻辑以 `.trae/skills/eatwhat-v1-ui/SKILL.md` 为 UI/交互设计基准

---

## 🚀 本地运行

### 1. 后端（端口 8000）

```bash
cd backend
pip install -r requirements.txt
python run.py            # 等价 uvicorn app.main:app --reload --port 8000
```

首次启动会自动 `init_db()`：建全部表、写入默认配置（审核开关、临期阈值）、种子数据（默认食材大类、封面图库）。
数据库文件生成在 `backend/eatwhat.db`（已 `.gitignore`，不入库）。

### 2. 前端（H5，端口 5173）

```bash
cd frontend
npm install
npm run dev:h5
```

浏览器打开 http://localhost:5173

### 3. 多端构建

```bash
npm run build:h5                  # H5 产物
npm run dev:mp-weixin             # 微信小程序（开发）
npm run build:mp-weixin           # 微信小程序（产物）
```

---

## 📁 目录结构

```
eatWhat/
├── backend/
│   ├── run.py                # 启动脚本
│   ├── requirements.txt
│   └── app/
│       ├── main.py          # FastAPI 入口：挂载全部路由
│       ├── db.py            # SQLite 建表 + 种子 + JSON 序列化 + 依赖
│       └── routers/         # recipes / fridge / candidate / shop / tips
│                            #   records / weights / ingredients / categories
│                            #   covers / configs / diners 等
├── frontend/
│   └── src/
│       ├── api/index.js     # 全部 API 客户端（recipe/candidate/fridge/shop/...）
│       ├── components/      # 自定义底部导航等
│       ├── pages/           # index/recipe/fridge/shop/mine 及全部二级页
│       ├── pages.json       # 路由与页面导航样式
│       └── App.vue
├── .trae/skills/eatwhat-v1-ui/SKILL.md   # UI/交互设计基准（维护中）
└── README.md
```

---

## 🔌 API 概览

| 模块 | 主要端点 |
| --- | --- |
| 菜谱 | `GET/POST /recipes`，`GET/PUT/DELETE /recipes/{id}` |
| 候选（吃这些） | `GET/POST /candidates`，`POST /candidates/{id}/toggle`，`DELETE /candidates/{id}` |
| 待采购 / 在库 | `GET/POST/DELETE /purchase`、`/fridge` |
| 食材库 | `GET/POST /ingredients`，`PUT/DELETE /ingredients/{id}` |
| 食材大类 | `GET/POST /categories`，`PUT/DELETE /categories/{id}`，排序 |
| 封面图库 | `GET/POST /covers`，`PUT/DELETE /covers/{id}`，排序 |
| 餐厅 | `GET/POST /shops`，`PUT/DELETE /shops/{id}` |
| 厨房技巧 | `GET/POST /tips`，`POST /tips/{id}/approve`、`/tips/{id}/reject` |
| 干饭记录 | `GET/POST /records`，`PUT/DELETE /records/{id}` |
| 体重 | `GET/POST /weights`，`PUT/DELETE /weights/{id}` |
| 干饭成员 | `GET/POST /diners` |
| 配置 | `GET/POST /configs/{key}` |

---

## 🧩 设计要点（避免踩坑）

- **派生数据一律实时计算，不存冗余**：临期/过期状态与天数、计时 elapsed、待采购量均由原始数据现算。
- **缺货代入 / 移除回退在单事务中原子完成**：候选的 `subs` 记录每次代入待采购的量，移除时按量回退，扣到 0 删除对应行。
- **餐厅候选只进候选列表，不参与待采购计算**。
- **食材库独立于冰箱库存**：菜谱所需 = 需求，冰箱在库/待采购 = 库存，两者解耦维护。
- **封面图库为管理员维护实体**：`covers` 表（emoji + 渐变 + 排序），菜谱封面未设时按 id 轮换默认渐变回退。
- **参考菜谱（source=admin）只读**：不可编辑/删除，仅管理员在 PC 管理端录入。
- **第一版为演示式权限**：无登录体系，管理员身份用前端本地 `eat_admin` 开关标记（MVP 语义）。
- **已升级为真登录体系**：见下文「登录 & 鉴权」。

---

## 🔐 登录 & 鉴权（已落地）

- **H5 / App 端**：邮箱验证码登录（登录页）。
- **微信小程序**：启动即静默 `wx.login` 换 openid（未配 mp_appid/secret 时用 `mock_openid` 稳定化）；登录后可绑定邮箱。
- **写操作鉴权**：未登录（无用户 token / 管理台令牌）一律 401；`get_write_user` 依赖同时接受用户 token 或管理台独立令牌。
- **PC 管理端**：口令登录（配置表 `admin_passcode`，默认 123456），后端签发独立管理员令牌 `X-Admin-Token`，与用户端 `eat_token` 并存。
- **openid 唯一**：`CREATE UNIQUE INDEX idx_users_openid ON users(openid)`，一个微信号一个账号。

---

## 🚀 生产部署（已实测）

详见 [DEPLOY.md](file:///d:/myProject/eatWhat/DEPLOY.md)。速查：

| 项 | 值 |
|---|---|
| 后端 | Alibaba Cloud Linux 3 + Python 3.11 + FastAPI + SQLite |
| 进程守护 | systemd 直接调 uvicorn（`--workers 4 --host 127.0.0.1 --port 8001`） |
| 反代 | Caddy HTTPS（Let's Encrypt 自动签） |
| API 域名 | `https://eatwhat.icefun.cn` |
| 小程序 MP_BASE | `https://eatwhat.icefun.cn/api`（Caddy 只接 `/api/*`，必须带前缀） |
| Caddyfile 关键 | `handle /api/* { uri strip_prefix /api; reverse_proxy 127.0.0.1:8001 }` |
| 微信合法域名 | 配一次 `https://eatwhat.icefun.cn` 即可覆盖 `/api/*` 所有请求 |

---

## 🎨 Emoji 查找（项目里大量用到）

菜谱封面 emoji、tabBar 图标、口味标签候选、食材图标池、大类图标——都从这里挑：

| 站 | 特点 |
|---|---|
| **https://emojipedia.org** | 最全：分类浏览、各平台渲染预览、搜索快 |
| https://getemoji.com | 点击复制即用 |
| https://www.webfx.com/tools/emoji-cheat-sheet/ | 分类清晰（食物/动物/手/符号…） |

**后端 emoji 池由管理员在系统配置里维护**（`recipe_emoji_pool` / `ingredient_icon_pool` / `cat_icon_pool`）。

---

## 📄 License

MIT