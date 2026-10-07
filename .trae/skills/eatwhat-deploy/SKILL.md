---
name: "eatwhat-deploy"
description: "FastAPI + Caddy + systemd 裸机/云主机部署流程。Invoke when user asks to deploy backend, update production, write Caddyfile/systemd service, backup SQLite DB, or troubleshoot production issues for eatWhat app."
---

# 吃啥 · 后端生产部署 Skill

> **适用场景**：eatWhat 项目的裸机 / 云主机生产部署与运维。所有 Python 3.11 + FastAPI + SQLite 项目可直接套用本模式。
> **标准架构**：Caddy（HTTPS + 反代）→ systemd（进程守护）→ venv（依赖隔离）→ uvicorn（多 worker）→ SQLite（WAL 模式，读写并发安全）

---

## 1. 服务器前置检查（先跑这几条再动手）

```bash
# Python 版本（FastAPI / Pydantic v2 最低 3.8，推荐 3.11）
python3.11 --version

# Caddy 状态（必须 running）
systemctl status caddy --no-pager

# systemd 存在（Alibaba Cloud Linux / CentOS / Debian / Ubuntu 都有）
systemctl --version

# 端口占用（本项目固定 8001，因为其它服务可能占了 8000）
ss -tlnp
```

---

## 2. 项目结构（部署包要传哪些）

```
eatWhat/
├── backend/                    ← 整个上传
│   ├── app/                    ← FastAPI（入口 main.py，路由在 routers/）
│   │   └── db.py               ← DB 路径：Path(__file__).resolve().parent.parent / "eatwhat.db"
│   ├── requirements.txt        ← fastapi / uvicorn / pydantic
│   ├── run.py                  ← 本地开发用（reload=True），生产**不用**它
│   └── eatwhat.db              ← 单独传（含 mp_appid/secret/SMTP + 用户数据）
└── frontend/                   ← 源码不上服务器；只传构建产物
    └── dist/build/mp-weixin/   ← 微信小程序构建产物（给开发者工具用）
```

**DB 路径关键**：`backend/app/db.py` 里硬编码了 `backend/eatwhat.db`，不依赖环境变量。所以把 DB 放 backend 目录下就行，换机器无感知。

---

## 3. 首次部署（从零开始）

### 3.1 本地打包（Windows PowerShell）

排除 .git / node_modules / dist / venv / .db / __pycache__ / 设计文档，只传代码。

```powershell
$staging = "$env:TEMP\eatwhat"
if (Test-Path $staging) { Remove-Item $staging -Recurse -Force }

# robocopy 镜像拷贝（排除垃圾）
robocopy "项目根目录" $staging /MIR `
    /XD .git node_modules dist unpackage __pycache__ venv .venv .hbuilderx bin web .trae `
    /XF eatwhat.db eatwhat.db-shm eatwhat.db-wal *.pyc *.DS_Store *.local README.md DESIGN.md prototype_v1.html cover-share.jpg deploy.ps1 `
    /NFL /NDL /NJH /NJS /NP /NS /NC | Out-Null

# 压缩
tar -czf "$env:TEMP\eatwhat-deploy.tar.gz" -C $env:TEMP eatwhat
# 通常 < 200 KB

# 2 个 SCP（IP / 目录换成实际值）
scp "$env:TEMP\eatwhat-deploy.tar.gz" root@服务器IP:/部署根目录/
scp "项目根目录\backend\eatwhat.db"     root@服务器IP:/部署根目录/
```

### 3.2 服务器端（SSH）

```bash
# === 解压 ===
cd /部署根目录
rm -rf eatwhat
mkdir eatwhat
tar -xzf eatwhat-deploy.tar.gz -C eatwhat --strip-components=1
mv eatwhat.db eatwhat/backend/

# === venv + 装依赖 ===
cd /部署根目录/eatwhat/backend
/usr/bin/python3.11 -m venv .venv     # dot 开头，跟现有项目风格对齐
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt

# === 手动试跑（前台，确认能起来再上 systemd）===
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8001 --workers 4 &
sleep 3
curl http://127.0.0.1:8001/health       # 预期 {"status":"ok"}
pkill -f "uvicorn app.main:app.*8001"
```

### 3.3 systemd service（固定模板）

```bash
sudo tee /etc/systemd/system/eatwhat.service > /dev/null << 'EOF'
[Unit]
Description=EatWhat FastAPI Backend
After=network.target

[Service]
User=root
Group=root
WorkingDirectory=/部署根目录/eatwhat/backend
ExecStart=/部署根目录/eatwhat/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8001 --workers 4
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

**端口说明**：uvicorn 绑 `127.0.0.1`（安全，只本机访问），Caddy 反代到它。8000 常被其它服务占，本项目固定用 **8001**。改端口时 systemd `--port 800X` 和 Caddyfile 反代目标一起改。

### 3.4 Caddyfile 追加（对齐现有写法）

```bash
sudo tee -a /etc/caddy/Caddyfile > /dev/null << 'EOF'

# ===== 吃啥 =====
你的子域名.主域名 {
    reverse_proxy 127.0.0.1:8001
}
EOF

sudo caddy validate --config /etc/caddy/Caddyfile && sudo systemctl reload caddy
curl https://你的子域名.主域名/health
```

**Caddy 自动申请 HTTPS 证书**，要求：
- 域名 DNS 解析到本服务器公网 IP
- 国内服务器域名已 ICP 备案

### 3.5 三步验证（全部绿勾才算上线）

| # | 命令 | 预期 |
|---|---|---|
| 1 | `systemctl status eatwhat --no-pager` | **active (running)**，无红字 |
| 2 | `curl http://127.0.0.1:8001/health` | `{"status":"ok"}` |
| 3 | `curl https://你的域名/health` | `{"status":"ok"}` + HTTP 200 |

---

## 4. 增量更新

### 4.1 只改 Python 代码（最常见）

```bash
# 本地重新打包 + SCP
scp "$env:TEMP\eatwhat-deploy.tar.gz" root@服务器IP:/部署根目录/

# 服务器端
cd /部署根目录/eatwhat
mv backend/eatwhat.db /tmp/eatwhat.db.bak       # 先挪出 DB 防覆盖
tar -xzf /部署根目录/eatwhat-deploy.tar.gz -C /部署根目录/eatwhat --strip-components=1
mv /tmp/eatwhat.db.bak backend/eatwhat.db

# requirements.txt 没变就跳过下面这条
source backend/.venv/bin/activate && pip install -r backend/requirements.txt

sudo systemctl restart eatwhat
sleep 2
curl http://127.0.0.1:8001/health
```

### 4.2 只改配置（mp_appid / SMTP / admin_passcode）

这些在 SQLite `configs` 表里，**不用改代码，不用重启**。

- 管理台改：浏览器打开 → 管理端(PC) → 系统配置 → 改完 blur 自动保存
- curl 直接打 API：
```bash
curl -X PUT https://你的域名/api/configs/配置key \
    -H 'Content-Type: application/json' \
    -H 'X-Admin-Token: 管理台令牌' \
    -d '{"value":"新值"}'
```

### 4.3 更新前端 H5 / 微信小程序

```bash
# H5 构建 + 传服务器（Caddy 静态托管）
cd frontend
npm run build:h5
scp -r dist/build/h5/* root@服务器IP:/部署根目录/eatwhat/web/

# 微信小程序构建（给开发者工具用，不传服务器）
npm run build:mp-weixin
```

Caddyfile 配 H5 静态 + API 反代同域时：
```
你的子域名.主域名 {
    root * /部署根目录/eatwhat/web
    file_server

    handle /api/* {
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
# 备份（建议 crontab 每天跑）
cp /部署根目录/eatwhat/backend/eatwhat.db \
   /部署根目录/eatwhat/backend/eatwhat.db.bak.$(date +%Y%m%d)

# 安全备份方式（防止进程正在写导致数据不完整）
sqlite3 /部署根目录/eatwhat/backend/eatwhat.db \
    ".backup /tmp/eatwhat.db.fresh"

# 恢复
cp /path/to/eatwhat.db.bak /部署根目录/eatwhat/backend/eatwhat.db
sudo systemctl restart eatwhat

# 远端下载到本地
scp root@服务器IP:/部署根目录/eatwhat/backend/eatwhat.db 本地路径/
```

---

## 6. 运维命令速查

| 要做什么 | 命令 |
|---|---|
| 实时日志 | `journalctl -u eatwhat -f` |
| 最近 100 行日志 | `journalctl -u eatwhat -n 100 --no-pager` |
| 状态 | `systemctl status eatwhat --no-pager` |
| 重启 | `sudo systemctl restart eatwhat` |
| 停服 | `sudo systemctl stop eatwhat` |
| 端口 | `ss -tlnp \| grep 8001` |
| 进程 | `ps aux \| grep uvicorn \| grep -v grep` |
| worker 数 | `ps aux \| grep "workers 4" \| wc -l` |
| Caddy 状态 | `systemctl status caddy --no-pager` |
| Caddyfile 重载 | `sudo systemctl reload caddy` |
| Caddyfile 语法校验 | `sudo caddy validate --config /etc/caddy/Caddyfile` |

---

## 7. 常见问题排查

### 7.1 systemd 起不来

```bash
journalctl -u eatwhat --no-pager     # 完整错误
ls -la /部署根目录/eatwhat/backend/.venv/bin/uvicorn   # venv 路径对不对
cat /etc/systemd/system/eatwhat.service | grep WorkingDirectory  # 工作目录对不对
```

### 7.2 SQLite `database is locked`

已在 `init_db()` 里设 `PRAGMA journal_mode=WAL`，多 worker 读写不阻塞。如果还锁：
```bash
sqlite3 /部署根目录/eatwhat/backend/eatwhat.db ".stats"
sqlite3 /部署根目录/eatwhat/backend/eatwhat.db "PRAGMA journal_mode=DELETE"  # 临时调试
```

### 7.3 mp_appid/secret 配了但登录报错

```bash
sqlite3 /部署根目录/eatwhat/backend/eatwhat.db \
    "SELECT key, substr(value,1,10) FROM configs WHERE key LIKE 'mp_%'"
```
FastAPI 每次 `/auth/login` 都实时读 configs 表（`get_config()` 每次都查 DB），**不需要重启**。

### 7.4 Caddy HTTPS 证书申请失败

```bash
journalctl -u caddy -f

# 常见原因：
# 1. 域名没备案（国内服务器）
# 2. DNS 没解析到本服务器
# 3. 80 端口被防火墙挡了（HTTP-01 验证要 80）
# 4. Caddyfile 写错（先用 caddy validate 检查）
```

### 7.5 微信小程序合法域名

生产 API 必须同时满足：
- **HTTPS** + **域名**（不能用 IP / HTTP）
- 端口 **443**（Caddy 自动处理）
- 国内服务器域名完成 **ICP 备案**
- 微信公众平台 → 开发 → 服务器域名 加 `https://你的域名`

### 7.6 本地 vs 生产差异

| 项 | 本地开发 | 生产 |
|---|---|---|
| uvicorn | run.py（reload=True, 单 worker） | systemd 直接调 uvicorn（workers=4, 无 reload） |
| DB | `backend/eatwhat.db` | 同位置 `backend/eatwhat.db` |
| H5 API | vite 代理 `/api` | Caddy 反代 `/api/*` |
| 小程序 API | `request.js MP_BASE` | 必须 `https://你的域名`（不能 IP） |

---

## 8. 安全注意

1. **后端只绑 127.0.0.1** —— 8001 不对外暴露，外网只能走 Caddy 443
2. **管理台口令** `admin_passcode` 默认 123456，上线后必改（管理台 → 系统配置）
3. **DB 文件权限** 设为 600：
   ```bash
   chown root:root /部署根目录/eatwhat/backend/eatwhat.db
   chmod 600 /部署根目录/eatwhat/backend/eatwhat.db
   ```
4. **Caddy 自动续期** HTTPS 证书，不用手动管

---

*版本：2026-10-07，基于 Alibaba Cloud Linux 3 + Python 3.11 + Caddy + systemd + uvicorn 4 worker 实测*
