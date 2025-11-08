@echo off
chcp 936 >nul
setlocal EnableDelayedExpansion

REM 修复管理员模式下%CD%变成system32的问题
REM 使用脚本所在目录作为工作目录
cd /d "%~dp0"
set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

REM 检查conda环境（项目本地环境）
set CONDA_ENV_PATH=%SCRIPT_DIR%\conda_env
set MINICONDA_ROOT=%SCRIPT_DIR%\Miniconda3

REM 检测路径是否包含非ASCII字符（中文等）
REM 使用PowerShell进行更可靠的检测
set "TEMP_CHECK_PATH=%SCRIPT_DIR%"
powershell -Command "$path = '%TEMP_CHECK_PATH%'; if ($path -match '[^\x00-\x7F]') { exit 1 } else { exit 0 }" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    REM 路径包含中文，使用磁盘根目录的Miniconda
    set MINICONDA_ROOT=%~d0\Miniconda3
)

where conda >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] 未检测到 Conda
    echo 请先运行 步骤1-首次安装.bat 安装 Miniconda
    pause
    exit /b 1
)

REM 尝试获取实际的Miniconda路径（处理system32情况）
for /f "delims=" %%i in ('conda info --base 2^>nul') do set "MINICONDA_ROOT=%%i"

if not exist "%CONDA_ENV_PATH%\python.exe" (
    echo [ERROR] Conda环境不存在
    echo 请先运行 步骤1-首次安装.bat 创建环境
    pause
    exit /b 1
)

REM 激活conda环境
REM 使用MINICONDA_ROOT变量，支持中文路径
if exist "%MINICONDA_ROOT%\Scripts\activate.bat" (
    call "%MINICONDA_ROOT%\Scripts\activate.bat" "%CONDA_ENV_PATH%" 2>nul
    if %ERRORLEVEL% neq 0 (
        REM 尝试使用conda activate作为备用
        call conda activate "%CONDA_ENV_PATH%" 2>nul
    )
) else (
    REM 如果没有本地Miniconda，使用系统conda
    call conda activate "%CONDA_ENV_PATH%" 2>nul
)

if %ERRORLEVEL% neq 0 (
    echo [ERROR] 无法激活环境
    echo 环境路径: %CONDA_ENV_PATH%
    echo Miniconda路径: %MINICONDA_ROOT%
    echo 请检查Conda是否正确安装或重新运行 步骤1-首次安装.bat
    pause
    exit /b 1
)

REM 检查是否有便携版 Git
if exist "PortableGit\cmd\git.exe" (
    set "GIT=%SCRIPT_DIR%\PortableGit\cmd\git.exe"
    set "PATH=%SCRIPT_DIR%\PortableGit\cmd;%PATH%"
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
