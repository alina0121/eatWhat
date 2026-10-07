# 吃啥 · 后端生产部署手册

> **适用场景**：裸机 / 云主机（Alibaba Cloud Linux 3、CentOS 7+、Debian 12、Ubuntu 22.04 均可）
> **本项目的部署固定模式**：Caddy 反代 + systemd 守护 + venv + uvicorn 多 worker + SQLite WAL 模式

---

## 1. 前置条件（服务器先确认一遍）

```bash
# 必须有
python3.11 --version         # ≥ 3.11（FastAPI / Pydantic v2 最低 3.8，推荐 3.11）
systemctl status caddy       # 必须 running，反代靠它
systemctl --version         # Alibaba Cloud Linux 3 / CentOS 系有 systemd

# 不是必须但建议
which scp tar curl
ss -tlnp                    # 看端口有没有被占（本项目用 8001）
```

---

## 2. 项目结构（部署时要传哪些）

```
eatWhat/
├── backend/                    ← 后端代码，整个上传
│   ├── app/                    ← FastAPI 应用（入口 main.py，路由在 routers/）
│   │   ├── db.py               ← DB 访问层，DB 路径是相对于本文件的 ../eatwhat.db
│   │   └── routers/            ← 所有业务路由
│   ├── requirements.txt        ← fastapi / uvicorn / pydantic（无第三方重依赖）
│   ├── run.py                  ← 本地开发用（reload=True），生产**不用**它
│   └── eatwhat.db              ← SQLite 文件，**单独传**（含 mp_appid/secret/SMTP 配置 + 用户数据）
├── frontend/                   ← 前端源码，开发机本地用；服务器不需要源码
│   └── dist/build/mp-weixin/   ← 微信小程序构建产物，给微信开发者工具用
└── web/                        ← （可选）H5 构建产物，Caddy 静态托管用
```

**关键**：`backend/app/db.py` 里 DB 路径是 `Path(__file__).resolve().parent.parent / "eatwhat.db"`，即 **DB 永远是 `backend/eatwhat.db`**，所以只要把 `eatwhat.db` 放 backend 目录下就行，不依赖环境变量。

---

## 3. 首次部署（从零开始）

### 3.1 本地打包（Windows PowerShell）

```powershell
# 清干净：排除 .git / node_modules / dist / venv / .db / __pycache__
$staging = "$env:TEMP\eatwhat"
if (Test-Path $staging) { Remove-Item $staging -Recurse -Force }
robocopy d:\myProject\eatWhat $staging /MIR `
    /XD .git node_modules dist unpackage __pycache__ venv .venv .hbuilderx bin web .trae `
    /XF eatwhat.db eatwhat.db-shm eatwhat.db-wal *.pyc *.DS_Store *.local README.md DESIGN.md prototype_v1.html cover-share.jpg deploy.ps1 `
    /NFL /NDL /NJH /NJS /NP /NS /NC | Out-Null

# 压缩
tar -czf "$env:TEMP\eatwhat-deploy.tar.gz" -C $env:TEMP eatwhat
# 产物：C:\Users\你\AppData\Local\Temp\eatwhat-deploy.tar.gz（通常 < 200 KB）

# 单独传 DB（含真实配置和数据）
scp d:\myProject\eatWhat\backend\eatwhat.db root@服务器IP:/mydata/
scp $env:TEMP\eatwhat-deploy.tar.gz root@服务器IP:/mydata/
```

### 3.2 服务器端（SSH 进去跑）

```bash
# === 解压 ===
cd /mydata
rm -rf eatwhat
mkdir eatwhat
tar -xzf eatwhat-deploy.tar.gz -C eatwhat --strip-components=1
mv eatwhat.db eatwhat/backend/

# 此时目录：
# /mydata/eatwhat/backend/app/...
# /mydata/eatwhat/backend/requirements.txt
# /mydata/eatwhat/backend/eatwhat.db    ← 你拷过来的

# === venv + 装依赖 ===
cd /mydata/eatwhat/backend
/usr/bin/python3.11 -m venv .venv     # dot 开头 .venv，跟 myinvesttools 一致
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt

# === 手动试跑（前台，确认能起来再上 systemd）===
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8001 --workers 4 &
sleep 3
curl http://127.0.0.1:8001/health
# 预期 {"status":"ok"}
pkill -f "uvicorn app.main:app.*8001"
```

### 3.3 systemd service

```bash
sudo tee /etc/systemd/system/eatwhat.service > /dev/null << 'EOF'
[Unit]
Description=EatWhat FastAPI Backend
After=network.target

[Service]
User=root
Group=root
WorkingDirectory=/mydata/eatwhat/backend
ExecStart=/mydata/eatwhat/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8001 --workers 4
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl start eatwhat
sudo systemctl status eatwhat --no-pager
curl http://127.0.0.1:8001/health
```

**端口说明**：uvicorn 绑定 `127.0.0.1`（只给本机访问，安全），Caddy 反代到它。myinvesttools 占了 8000，吃啥用 **8001**。如果要改端口，systemd 里 `--port 800X` 和 Caddyfile 里的反代目标一起改。

### 3.4 Caddyfile 追加（对齐现有写法）

```bash
sudo tee -a /etc/caddy/Caddyfile > /dev/null << 'EOF'

# ===== 吃啥 =====
eatwhat.icefun.cn {
    # 前端（H5 / 小程序）统一走 /api/*，Caddy strip_prefix 后反代到后端根路径
    # 否则 FastAPI 找不到 /api/auth/login 这种带前缀的路由（后端是根挂载）
    handle /api/* {
        uri strip_prefix /api
        reverse_proxy 127.0.0.1:8001
    }
}
EOF

sudo caddy validate --config /etc/caddy/Caddyfile && sudo systemctl reload caddy
curl https://eatwhat.icefun.cn/health
```

**Caddy 会自动申请 Let's Encrypt HTTPS 证书**，要求：
- 域名 DNS 解析到本服务器公网 IP
- 域名在阿里云备案通过（国内服务器必须）

### 3.5 三步验证清单（全部绿勾才算上线成功）

| # | 命令 | 预期 |
|---|---|---|
| 1 | `systemctl status eatwhat --no-pager` | **active (running)**，无红字报错 |
| 2 | `curl http://127.0.0.1:8001/health` | `{"status":"ok"}` |
| 3 | `curl https://eatwhat.icefun.cn/health` | `{"status":"ok"}` + HTTP 200 |

---

## 4. 增量更新（改了代码后上线）

### 4.1 只改了 Python 代码（最常见）

```bash
# 本地重新打包 + SCP
scp $env:TEMP\eatwhat-deploy.tar.gz root@服务器IP:/mydata/

# 服务器端
cd /mydata/eatwhat
# 先把 DB 挪出来（防止解压覆盖）
mv backend/eatwhat.db /tmp/eatwhat.db.bak

# 解包覆盖
tar -xzf /mydata/eatwhat-deploy.tar.gz -C /mydata/eatwhat --strip-components=1

# DB 挪回去
mv /tmp/eatwhat.db.bak backend/eatwhat.db

# 如果 requirements.txt 没变就跳过下面这条
# source backend/.venv/bin/activate && pip install -r backend/requirements.txt

# 重启（热加载 SQLite WAL 足够）
sudo systemctl restart eatwhat
sleep 2
curl http://127.0.0.1:8001/health
```

### 4.2 改了配置（mp_appid / SMTP / admin_passcode 等）

这些配置存在 SQLite 的 `configs` 表里，**不用改代码**。两种方式：

**方式 A：管理台改（推荐，即时生效）**
- 浏览器打开 `https://eatwhat.icefun.cn` → 管理端（PC 宽屏）→ 系统配置

**方式 B：用 curl 直接打 API**
```bash
curl -X PUT https://eatwhat.icefun.cn/api/configs/mp_secret \
    -H 'Content-Type: application/json' \
    -H 'X-Admin-Token: 你的管理台令牌' \
    -d '{"value":"新值"}'
```
管理台令牌从 POST /admin/login 拿到。

### 4.3 更新前端 H5 静态 / 微信小程序

```bash
# H5 构建
cd frontend
npm run build:h5   # 产出 dist/build/h5/

# 传到服务器（假设你用 /mydata/eatwhat/web 作为 Caddy 静态目录）
scp -r dist/build/h5/* root@服务器IP:/mydata/eatwhat/web/

# 微信小程序构建
npm run build:mp-weixin   # 产出 dist/build/mp-weixin/
# 这包给微信开发者工具「上传」按钮用，不需要传到服务器
```

Caddyfile 要配 H5 静态 + API 反代同域时：
```
eatwhat.icefun.cn {
    root * /mydata/eatwhat/web
    file_server

    handle /api/* {
        uri strip_prefix /api
        reverse_proxy 127.0.0.1:8001
    }

    handle {
        respond /index.html 200
    }
}
```

---

## 5. 数据库备份 / 恢复

```bash
# 一键备份（建议加 crontab 每天跑）
cp /mydata/eatwhat/backend/eatwhat.db \
   /mydata/eatwhat/backend/eatwhat.db.bak.$(date +%Y%m%d)

# 恢复
cp /path/to/eatwhat.db.bak.20261007 /mydata/eatwhat/backend/eatwhat.db
sudo systemctl restart eatwhat

# 远端下载到本地
scp root@服务器IP:/mydata/eatwhat/backend/eatwhat.db d:\myProject\eatWhat\backend\
```

**为什么不能直接用 SQLite WAL 文件**：服务器上 WAL 文件（`eatwhat.db-wal` / `-shm`）是 FastAPI 运行时临时持有的，拷的时候进程可能还在写 → 数据不完整。先停服务再拷，或者用 `sqlite3 .backup`：
```bash
sqlite3 /mydata/eatwhat/backend/eatwhat.db ".backup /tmp/eatwhat.db.fresh"
```

---

## 6. 运维常用命令速查

| 要做什么 | 命令 |
|---|---|
| 看实时日志 | `journalctl -u eatwhat -f` |
| 看最近 100 行 | `journalctl -u eatwhat -n 100 --no-pager` |
| 看状态 | `systemctl status eatwhat --no-pager` |
| 重启 | `sudo systemctl restart eatwhat` |
| 停服务 | `sudo systemctl stop eatwhat` |
| 看端口 | `ss -tlnp \| grep 8001` |
| 看进程 | `ps aux \| grep uvicorn \| grep -v grep` |
| uvicorn worker 数 | `ps aux \| grep "workers 4" \| wc -l` |
| 查 Caddy 状态 | `systemctl status caddy --no-pager` |
| 重载 Caddyfile | `sudo systemctl reload caddy` |
| 验证 Caddyfile 语法 | `sudo caddy validate --config /etc/caddy/Caddyfile` |

---

## 7. 常见问题排查

### 7.1 systemd 起不来

```bash
# 看完整错误
journalctl -u eatwhat --no-pager

# 最常见：venv 路径不对（.venv 前有没有 .）
ls -la /mydata/eatwhat/backend/.venv/bin/uvicorn

# 最常见：工作目录不对
cat /etc/systemd/system/eatwhat.service | grep WorkingDirectory
```

### 7.2 SQLite 多 worker 死锁

已在 `init_db()` 里设了 `PRAGMA journal_mode=WAL`，多 worker 读写不阻塞。如果仍然 `database is locked`：
```bash
# 看当前连接数
sqlite3 /mydata/eatwhat/backend/eatwhat.db ".stats"

# 强制关 WAL（临时调试用，不建议长期）
sqlite3 /mydata/eatwhat/backend/eatwhat.db "PRAGMA journal_mode=DELETE"
```

### 7.3 mp_appid/secret 配了但登录报错

```bash
# 看服务器上 configs 表实际值
sqlite3 /mydata/eatwhat/backend/eatwhat.db \
    "SELECT key, substr(value,1,10) FROM configs WHERE key LIKE 'mp_%'"
```
配好后**不需要重启**，FastAPI 每次 `/auth/login` 都实时读 configs 表（`get_config()` 每次都查 DB）。

### 7.4 Caddy HTTPS 证书申请失败

```bash
# 看 Caddy 日志
journalctl -u caddy -f

# 常见原因：
# 1. 域名没备案（国内服务器）
# 2. DNS 没解析到本服务器
# 3. 80 端口被防火墙挡了（Caddy 要 80 端口做 HTTP-01 验证）
# 4. Caddyfile 写错了（用 caddy validate 先检查）
```

### 7.5 微信小程序合法域名要求

生产 API 必须同时满足：
- **HTTPS** + **域名**（不能用 IP，不能用 HTTP）
- 端口 **443**（Caddy 自动处理）
- 国内服务器的域名必须完成 **ICP 备案**
- 微信公众平台 → 开发 → 开发管理 → 服务器域名 里加 `https://eatwhat.icefun.cn`

### 7.6 本地开发 vs 生产的关键差异

| 项 | 本地开发 | 生产 |
|---|---|---|
| uvicorn | `run.py`（reload=True, 单 worker） | systemd 直接调 uvicorn（workers=4, 无 reload） |
| DB | `backend/eatwhat.db` | 同一个位置 `backend/eatwhat.db` |
| 前端 API | H5 走 vite 代理 `/api`；小程序走 `MP_BASE` | **小程序必须** `const MP_BASE = 'https://eatwhat.icefun.cn/api'`（Caddy 只接管 `/api/*` 前缀，后端路由根挂载） |
| CORS | 开发允许 `*` | 生产也允许 `*`（反代在 Caddy 层解决跨域） |

---

## 8. 安全注意

1. **后端只绑 127.0.0.1** —— 端口 8001 不对外暴露，外网只能走 Caddy 反代的 443
2. **管理台口令** `admin_passcode` 默认 123456，上线后必改（管理台 → 系统配置）
3. **mp_secret / smtp_pass** 这些敏感配置存在 SQLite 里，DB 文件权限设为 `root:root 600`：
   ```bash
   chown root:root /mydata/eatwhat/backend/eatwhat.db
   chmod 600 /mydata/eatwhat/backend/eatwhat.db
   ```
4. **Caddy** 自动申请 HTTPS 证书，过期前自动续期，不用手动管

---

*文档版本：2026-10-07，基于 Alibaba Cloud Linux 3 + Python 3.11 + Caddy + systemd + uvicorn 实测*

---

## 9. 踩坑排障速查

| 现象 | 根因 | 修 |
|---|---|---|
| 体验版扫码**白屏**无报错 | `request.js` 顶层 `ensureLogin()` 无 catch → unhandled rejection | `ensureLogin()` → `ensureLogin().catch(() => {})` |
| 小程序请求 `404` 但 H5 正常 | MP_BASE 没带 `/api`，Caddy 只接管 `/api/*` 前缀 | `const MP_BASE = 'https://eatwhat.icefun.cn/api'`（不是直接域名） |
| Caddyfile 重载报 `ambiguous site definition` | 同名域名写了两段 | 覆盖整个 Caddyfile 而非 tee 追加 |
| Let's Encrypt finalize `context deadline exceeded` | 国内服务器连 acme-v02 偶发超时 | `systemctl restart caddy` 重试（HTTP-01 验证已过）；仍不行换阿里云免费证书 |
| 管理台登录后写操作仍 `401` | 登口令只存了 `eat_admin` 标记，没存 `eat_admin_token` | `/admin/login` 返回的 token 必须 `uni.setStorageSync(ADMIN_TOKEN_KEY, token)` |
| `python run.py prod` 多 worker 报 `Directory ... does not exist` | 生产没构建 `web/` 静态，main.py 硬挂载会崩 | 改成目录存在才挂载（`if _WEB_DIR.is_dir(): ...`） |
| SQLite WAL 分叉（进程间看不同步） | Python sqlite3 和 uvicorn 各开一连接池 | 关掉 WAL：`PRAGMA journal_mode=DELETE`；或统一经 uvicorn |

---

## 10. Emoji 查找（项目里大量用到 emoji：菜谱封面、tabBar、口味标签候选、食材图标池、大类图标）

| 站 | 特点 |
|---|---|
| **https://emojipedia.org** | 最全：分类浏览、iOS/Google/Apple 各平台渲染预览、搜索快、最新 emoji |
| https://getemoji.com | 点击复制即用，有设备过滤（手机/桌面/所有） |
| https://www.webfx.com/tools/emoji-cheat-sheet/ | 分类清晰（食物/动物/手/符号…），适合挑菜谱封面 |
| https://www.character-codes.com/emojis/ | 有 emoji → CSS 字符码对照，写样式时有用 |

**项目里 emoji 的三处来源**：
1. **后端 configs 表**：`recipe_emoji_pool`（菜谱封面 emoji 池）、`ingredient_icon_pool` / `cat_icon_pool`（食材/大类图标池）、`cover_grad_pool`（菜谱封面渐变）——管理台「系统配置」里维护
2. **前端硬编码候选**：口味标签候选（SKILL eatwhat-v1-ui 里有）、tabBar 图标（manifest.json pages）
3. **菜谱字段**：`recipes.em` 存单条封面 emoji（从 emoji_pool 里点选）

---

*文档版本：2026-10-08，Alibaba Cloud Linux 3 + Python 3.11 + Caddy + systemd + uvicorn 4 worker 实测*
