#!/usr/bin/env bash
# 出卷集成工作台 一键启动 (macOS / Linux)
set -e
cd "$(dirname "$0")"

echo "============================================"
echo " 出卷集成工作台 一键启动"
echo "============================================"

# ---- 后端虚拟环境与依赖 ----
if [ ! -x ".venv/bin/python" ]; then
  echo "[安装] 创建 Python 虚拟环境并安装后端依赖..."
  python3 -m venv .venv
  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/python -m pip install -r backend/requirements.txt
fi

# ---- 前端依赖 ----
if [ ! -d "frontend/node_modules" ]; then
  echo "[安装] 安装前端依赖..."
  (cd frontend && npm install)
fi

echo "[清理] 杀掉本项目残留的后端/前端进程..."
# 按命令行模式清理（含 uvicorn reload 父子进程与 vite）
pkill -f 'uvicorn main:app' 2>/dev/null || true
pkill -f 'exam_production_studio.*vite' 2>/dev/null || true
# 兜底：按端口释放 8000/5173
for p in 8000 5173; do
  pids=$(lsof -ti tcp:"$p" 2>/dev/null || true)
  [ -n "$pids" ] && kill -9 $pids 2>/dev/null || true
done
sleep 1

echo "[启动] 后端 http://127.0.0.1:8000  前端 http://localhost:5173"
.venv/bin/python -m uvicorn main:app --app-dir backend --port 8000 --reload &
BACK=$!
(cd frontend && npm run dev) &
FRONT=$!

trap "echo; echo '正在停止...'; kill $BACK $FRONT 2>/dev/null" EXIT INT TERM
echo "浏览器访问： http://localhost:5173  （按 Ctrl+C 停止）"
wait
