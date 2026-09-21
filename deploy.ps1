# 吃啥 · 一键上线脚本（固化部署流程）
# 用法：在 PowerShell 项目根目录执行  .\deploy.ps1
# 作用：装依赖 → 初始化/种子演示数据 → 启动服务

$ErrorActionPreference = "Stop"
Write-Host "==> [1/4] 检查 Python" -ForegroundColor Cyan
python --version

Write-Host "==> [2/4] 安装依赖" -ForegroundColor Cyan
python -m pip install -q -r backend\requirements.txt

Write-Host "==> [3/4] 初始化数据库 + 演示数据" -ForegroundColor Cyan
python backend\seed_demo.py

Write-Host "==> [4/4] 启动服务  http://localhost:8000/" -ForegroundColor Green
python backend\run.py