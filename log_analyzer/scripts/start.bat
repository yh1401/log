@echo off
chcp 65001 >nul

REM 切换到项目根目录
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..
cd /d "%PROJECT_ROOT%"

echo ==========================================
echo    启动日志分析系统
echo ==========================================
echo.

REM 检查虚拟环境是否存在
if not exist "venv" (
    echo 错误: 虚拟环境不存在！
    echo 请先运行 scripts\install.bat 安装依赖
    pause
    exit /b 1
)

REM 激活虚拟环境
echo 激活虚拟环境...
call venv\Scripts\activate.bat

REM 启动服务
echo 启动服务...
echo.
echo 服务地址: http://localhost:8000
echo 按 Ctrl+C 停止服务
echo.

cd web
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
