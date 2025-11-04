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
    set "GIT=%CD%\PortableGit\cmd\git.exe"
    set "PATH=%CD%\PortableGit\cmd;%PATH%"
) else (
    git --version >nul 2>&1
    if %ERRORLEVEL% == 0 (
        set GIT=git
    ) else (
        REM Git不可用，跳过版本检查
        goto :skip_version_check
    )
)

REM 使用Python脚本快速检查版本（避免批处理冒号问题）
python packaging\check_version.py --brief 2>nul

:skip_version_check
REM 切换到项目根目录
cd /d "%~dp0"

REM 启动 Qt 界面
echo 正在启动...
echo ========================================
echo.
python desktop_qt_ui\main.py
pause
