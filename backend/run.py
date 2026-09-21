# -*- coding: utf-8 -*-
"""启动脚本：python run.py 即可在 8000 端口起服务（开发模式 reload）。

也可手动：uvicorn app.main:app --reload --port 8000
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)