#!/bin/bash

# 切换到项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "=========================================="
echo "   启动日志分析系统"
echo "=========================================="
echo ""

# 检查虚拟环境是否存在
if [ ! -d "venv" ]; then
    echo "错误: 虚拟环境不存在！"
    echo "请先运行 ./scripts/install.sh 安装依赖"
    exit 1
fi

# 激活虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate

# 启动服务
echo "启动服务..."
echo ""
echo "服务地址: http://localhost:8000"
echo "按 Ctrl+C 停止服务"
echo ""

cd web
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
