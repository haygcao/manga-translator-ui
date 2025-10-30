@echo off
chcp 936 >nul
setlocal EnableDelayedExpansion

REM 激活虚拟环境
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo [ERROR] 虚拟环境不存在,请先运行 步骤1-首次安装.bat
    pause
    exit /b 1
)

REM 检查是否有便携版 Git
if exist "PortableGit\cmd\git.exe" (
    set PATH=%~dp0PortableGit\cmd;%PATH%
)

REM 启动 Qt 版本
python launch.py --ui qt --frozen
pause
