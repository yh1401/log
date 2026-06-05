#!/bin/bash

# 切换到项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "=========================================="
echo "   日志分析系统 - Linux/macOS 安装脚本"
echo "=========================================="
echo ""

# 检查 Python 版本
echo "检查 Python 版本..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "当前 Python 版本: $PYTHON_VERSION"

# 创建虚拟环境
echo ""
echo "创建虚拟环境..."
python3 -m venv venv

# 激活虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate

# 升级 pip
echo ""
echo "升级 pip..."
pip install --upgrade pip

# 安装依赖
echo ""
echo "安装项目依赖..."
pip install -r requirements.txt

echo ""
echo "=========================================="
echo "   安装完成！"
echo "=========================================="
echo ""
echo "启动服务："
echo "  ./scripts/start.sh"
echo ""
echo "或手动启动："
echo "  source venv/bin/activate"
echo "  cd web"
echo "  uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4"
echo ""
echo "访问地址："
echo "  http://localhost:8000"
echo ""
