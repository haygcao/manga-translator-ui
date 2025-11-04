@echo off
chcp 936 >nul
setlocal EnableDelayedExpansion

REM 检查conda环境（项目本地环境）
set CONDA_ENV_PATH=%CD%\conda_env

where conda >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] 未检测到 Conda
    echo 请先运行 步骤1-首次安装.bat 安装 Miniconda
    pause
    exit /b 1
)

if not exist "%CONDA_ENV_PATH%\python.exe" (
    echo [ERROR] Conda环境不存在
    echo 请先运行 步骤1-首次安装.bat 创建环境
    pause
    exit /b 1
)

REM 激活conda环境
call conda activate "%CONDA_ENV_PATH%"
if %ERRORLEVEL% neq 0 (
    echo [ERROR] 无法激活环境
    pause
    exit /b 1
)

REM 检查是否有便携版 Git
if exist "PortableGit\cmd\git.exe" (
    set "PATH=%CD%\PortableGit\cmd;%PATH%"
)

REM 切换到项目根目录(确保Python能正确找到模块)
cd /d "%~dp0"

REM 直接启动 Qt 界面
python desktop_qt_ui\main.py
pause
