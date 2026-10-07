# -*- coding: utf-8 -*-
"""启动脚本：

开发：    python run.py              (单 worker + reload)
生产：    python run.py prod         (多 worker，无 reload，配合 systemd)
          或  uvicorn app.main:app --workers 4 --host 0.0.0.0 --port 8000
"""
import sys
import uvicorn

if __name__ == "__main__":
    is_prod = len(sys.argv) > 1 and sys.argv[1] == "prod"
    if is_prod:
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            workers=4,        # 多 worker：按服务器 CPU 核数调，2-4 起步
            reload=False,
            log_level="info",
            access_log=True,
        )
    else:
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
        )
