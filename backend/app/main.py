# -*- coding: utf-8 -*-
"""
FastAPI 应用入口：CORS + 路由挂载 + 健康检查。

启动：cd backend && uvicorn app.main:app --reload --port 8000
（或直接 python run.py）
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.db import init_db
from app.routers import (
    admin, auth, candidates, categories, configs, diners, fridge, ingredients, mine, recipes, records, shops, taste_tags, tips, weights,
)

# 幂等初始化数据库（首次启动自动建表+种子）
init_db()

app = FastAPI(title="吃啥 · API", version="1.0")

# H5 前端开发跨域：第一阶段前端可跑在不同端口/静态服务，因此放开 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载各业务路由（auth 放在最前，其他路由依赖它的 get_optional_user）
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(mine.router)
app.include_router(configs.router)
app.include_router(recipes.router)
app.include_router(fridge.router)
app.include_router(ingredients.router)
app.include_router(categories.router)
app.include_router(candidates.router)
app.include_router(shops.router)
app.include_router(diners.router)
app.include_router(tips.router)
app.include_router(records.router)
app.include_router(weights.router)
app.include_router(taste_tags.router)


@app.get("/health")
def health():
    """健康检查，供上线脚本与前端探测用。"""
    return {"status": "ok"}


# 静态托管前端页面（可选）：API 路由注册在前，此挂载放在最后兜底，同源访问首页。
# 目录：项目根下的 web/。
# 生产环境通常由 Caddy / Nginx 托管 H5 静态、后端只跑 API —— 此时 web/ 目录不存在，
# 跳过挂载（Caddy 反代 `/api/*` 到后端，根路径 `/` 直接由 Caddy 处理）。
# 本地开发如果有 web/ 构建产物则自动挂载，访问 http://localhost:8000/ 即可打开应用。
_WEB_DIR = Path(__file__).resolve().parents[2] / "web"
if _WEB_DIR.is_dir():
    app.mount("/", StaticFiles(directory=_WEB_DIR, html=True), name="web")