#!/bin/bash

# Log Analyzer 多轮对话式日志分析系统启动脚本

echo "========================================="
echo "  Log Analyzer - 多轮对话式日志分析系统"
echo "========================================="
echo ""

# 切换到项目根目录
cd "$(dirname "$0")/.."

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 Python3，请先安装 Python3"
    exit 1
fi

# 检查依赖
echo "检查依赖..."
if ! python3 -c "import fastapi" &> /dev/null; then
    echo "安装依赖..."
    pip3 install -r requirements.txt
fi

# 启动应用
echo ""
echo "启动应用..."
echo "访问地址: http://localhost:8000"
echo "聊天界面: http://localhost:8000/chat"
echo "API文档: http://localhost:8000/docs"
echo ""
echo "按 Ctrl+C 停止服务"
echo ""

python3 -m uvicorn log_analyzer.web-langchain.app:app --reload --host 0.0.0.0 --port 8000
