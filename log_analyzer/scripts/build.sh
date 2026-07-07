#!/bin/bash

# ==========================================
# 日志分析系统 - 打包脚本
# ==========================================

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DIST_DIR="$PROJECT_ROOT/dist"

# 版本号
VERSION="1.0.0"
DATE=$(date +%Y%m%d)
PACKAGE_NAME="log_analyzer_v${VERSION}_${DATE}"

echo "=========================================="
echo "   日志分析系统 - 打包工具"
echo "=========================================="
echo ""
echo "项目根目录: $PROJECT_ROOT"
echo "输出目录: $DIST_DIR"
echo "包名称: $PACKAGE_NAME"
echo ""

# 创建输出目录
mkdir -p "$DIST_DIR"

# 切换到项目根目录
cd "$PROJECT_ROOT"

# 清理旧的打包文件
echo "清理旧的打包文件..."
rm -rf "$DIST_DIR/$PACKAGE_NAME"
rm -f "$DIST_DIR/${PACKAGE_NAME}.zip"

# 创建临时目录
echo "创建临时目录..."
mkdir -p "$DIST_DIR/$PACKAGE_NAME"

# 复制项目文件
echo "复制项目文件..."
rsync -av --exclude='venv' \
    --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='*.pyo' \
    --exclude='.git' \
    --exclude='.DS_Store' \
    --exclude='logs/*' \
    --exclude='tasks/*' \
    --exclude='users/*' \
    --exclude='uploads/*' \
    --exclude='data/*' \
    --exclude='checkpoints/*' \
    --exclude='logfile/*' \
    --exclude='.dbg/*' \
    --exclude='reports/*' \
    --exclude='auth/users.json' \
    --exclude='*.log' \
    --exclude='*.backup' \
    --exclude='*.bak' \
    --exclude='web/app.py.backup' \
    --exclude='dist' \
    --exclude='.idea' \
    --exclude='.vscode' \
    --exclude='*.swp' \
    --exclude='*.swo' \
    --exclude='docs/node_modules' \
    --exclude='node_modules' \
    --exclude='.pytest_cache' \
    --exclude='test_*' \
    --exclude='*.test.*' \
    --exclude='start_test.py' \
    --exclude='performance_test.py' \
    --exclude='concurrency_test.py' \
    --exclude='test_memory_adjust.py' \
    "$PROJECT_ROOT/" "$DIST_DIR/$PACKAGE_NAME/" 2>/dev/null

# 创建必要的空目录
echo "创建必要的目录结构..."
mkdir -p "$DIST_DIR/$PACKAGE_NAME/logs"
mkdir -p "$DIST_DIR/$PACKAGE_NAME/tasks"
mkdir -p "$DIST_DIR/$PACKAGE_NAME/users"
mkdir -p "$DIST_DIR/$PACKAGE_NAME/uploads"
mkdir -p "$DIST_DIR/$PACKAGE_NAME/data"
mkdir -p "$DIST_DIR/$PACKAGE_NAME/checkpoints"
mkdir -p "$DIST_DIR/$PACKAGE_NAME/reports"

# 添加 .gitkeep 文件
touch "$DIST_DIR/$PACKAGE_NAME/logs/.gitkeep"
touch "$DIST_DIR/$PACKAGE_NAME/tasks/.gitkeep"
touch "$DIST_DIR/$PACKAGE_NAME/users/.gitkeep"
touch "$DIST_DIR/$PACKAGE_NAME/uploads/.gitkeep"
touch "$DIST_DIR/$PACKAGE_NAME/data/.gitkeep"
touch "$DIST_DIR/$PACKAGE_NAME/checkpoints/.gitkeep"
touch "$DIST_DIR/$PACKAGE_NAME/reports/.gitkeep"

# 设置脚本执行权限
echo "设置脚本执行权限..."
chmod +x "$DIST_DIR/$PACKAGE_NAME/scripts/"*.sh

# 创建压缩包
echo "创建压缩包..."
cd "$DIST_DIR"
zip -r "${PACKAGE_NAME}.zip" "$PACKAGE_NAME" -x "*.DS_Store"

# 清理临时目录
echo "清理临时目录..."
rm -rf "$PACKAGE_NAME"

# 显示结果
echo ""
echo "=========================================="
echo "   打包完成！"
echo "=========================================="
echo ""
echo "压缩包位置:"
echo "  $DIST_DIR/${PACKAGE_NAME}.zip"
echo ""
echo "压缩包大小:"
ls -lh "${PACKAGE_NAME}.zip"
echo ""
echo "使用方法:"
echo "  1. 将压缩包发送给同事"
echo "  2. Linux/macOS: 解压后运行 ./scripts/install.sh"
echo "  3. Windows: 解压后运行 scripts\\install.bat"
echo ""
