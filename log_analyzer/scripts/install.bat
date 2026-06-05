@echo off
chcp 65001 >nul

REM 切换到项目根目录
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..
cd /d "%PROJECT_ROOT%"

echo ==========================================
echo    日志分析系统 - Windows 安装脚本
echo ==========================================
echo.

REM 检查 Python 版本
echo 检查 Python 版本...
python --version
echo.

REM 创建虚拟环境
echo 创建虚拟环境...
python -m venv venv
if %errorlevel% neq 0 (
    echo 创建虚拟环境失败！
    pause
    exit /b 1
)

REM 激活虚拟环境
echo 激活虚拟环境...
call venv\Scripts\activate.bat

REM 升级 pip
echo.
echo 升级 pip...
python -m pip install --upgrade pip

REM 安装依赖
echo.
echo 安装项目依赖...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo 安装依赖失败！
    pause
    exit /b 1
)

echo.
echo ==========================================
echo    安装完成！
echo ==========================================
echo.
echo 启动服务：
echo   scripts\start.bat
echo.
echo 或手动启动：
echo   venv\Scripts\activate
echo   cd web
echo   uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
echo.
echo 访问地址：
echo   http://localhost:8000
echo.
pause
