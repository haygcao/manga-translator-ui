@echo off
chcp 936 >nul
setlocal EnableDelayedExpansion

REM 设置 PYTHONUTF8=1 避免conda编码错误
set "PYTHONUTF8=1"

REM 修复管理员模式下%CD%变成system32的问题
REM 使用脚本所在目录作为工作目录
cd /d "%~dp0"
set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

REM 检查conda环境（兼容命名环境和路径环境）
set CONDA_ENV_NAME=manga-env
set CONDA_ENV_PATH=%SCRIPT_DIR%\conda_env
set "MINICONDA_ROOT="
set "DEFAULT_MINICONDA_ROOT=%SCRIPT_DIR%\Miniconda3"
set "ALT_MINICONDA_ROOT=%~d0\Miniconda3"
set "CONDA_REGISTRY_FOUND=0"
set "CONDA_VALID=0"
set "ENV_PATH="
set "ENV_PYTHON="
set "USE_DIRECT_ENV_PYTHON=0"
set "CONDA_ENV_MODE="
set "CONDA_REGISTRY_FOUND=0"
set "CONDA_VALID=0"
set "ENV_PATH="
set "ENV_PYTHON="
set "USE_DIRECT_ENV_PYTHON=0"
set "CONDA_ENV_MODE="

REM 检测路径是否包含非ASCII字符（中文等）
REM 使用PowerShell进行更可靠的检测
set "TEMP_CHECK_PATH=%SCRIPT_DIR%"
powershell -Command "$path = '%TEMP_CHECK_PATH%'; if ($path -match '[^\x00-\x7F]') { exit 1 } else { exit 0 }" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    REM 路径包含中文，使用磁盘根目录的Miniconda
    set "DEFAULT_MINICONDA_ROOT=%ALT_MINICONDA_ROOT%"
)

call :detect_conda_registry_s2

REM 优先检查本地 Miniconda
if exist "%DEFAULT_MINICONDA_ROOT%\Scripts\conda.exe" (
    set "MINICONDA_ROOT=%DEFAULT_MINICONDA_ROOT%"
    echo [INFO] 检测到本地 Miniconda: %MINICONDA_ROOT%
    goto :validate_detected_conda_s2
)
if /I not "%ALT_MINICONDA_ROOT%"=="%DEFAULT_MINICONDA_ROOT%" (
    if exist "%ALT_MINICONDA_ROOT%\Scripts\conda.exe" (
        set "MINICONDA_ROOT=%ALT_MINICONDA_ROOT%"
        echo [INFO] 检测到本地 Miniconda: %MINICONDA_ROOT%
        goto :validate_detected_conda_s2
    )
)

REM 再检查系统 Conda
if defined CONDA_EXE (
    for /f "delims=" %%i in ('"%CONDA_EXE%" info --base 2^>nul') do (
        if exist "%%i\Scripts\conda.exe" set "MINICONDA_ROOT=%%i"
    )
)
if not defined MINICONDA_ROOT (
    for /f "delims=" %%i in ('conda info --base 2^>nul') do (
        if exist "%%i\Scripts\conda.exe" set "MINICONDA_ROOT=%%i"
    )
)
if not defined MINICONDA_ROOT (
    for /f "delims=" %%i in ('where conda 2^>nul') do (
        if not defined MINICONDA_ROOT (
            if /I "%%~nxi"=="conda.exe" (
                for %%p in ("%%~dpi..") do if exist "%%~fp\Scripts\conda.exe" set "MINICONDA_ROOT=%%~fp"
            ) else if /I "%%~nxi"=="conda.bat" (
                for %%p in ("%%~dpi..") do if exist "%%~fp\Scripts\conda.exe" set "MINICONDA_ROOT=%%~fp"
            )
        )
    )
)

if not defined MINICONDA_ROOT (
    echo [ERROR] 未检测到 Conda
    echo 请先运行 步骤1-首次安装.bat 安装 Miniconda
    pause
    exit /b 1
)

:validate_detected_conda_s2
call :report_conda_registry_status_s2
call :validate_conda_root_s2
if "!CONDA_VALID!" neq "1" (
    echo [ERROR] 检测到 Conda，但校验失败: %MINICONDA_ROOT%
    echo 请先运行 步骤1-首次安装.bat 重新安装或修复 Miniconda
    pause
    exit /b 1
)
echo [OK] Conda 校验通过

:init_conda_cmd_s2
if exist "%MINICONDA_ROOT%\condabin\conda.bat" (
    set "PATH=%MINICONDA_ROOT%\condabin;%MINICONDA_ROOT%\Scripts;%PATH%"
) else if exist "%MINICONDA_ROOT%\Scripts\conda.exe" (
    set "PATH=%MINICONDA_ROOT%\Scripts;%PATH%"
)

:check_env_s2

REM 检查环境是否存在（优先命名环境）
REM 使用 /B 选项进行精确匹配行首，避免误匹配路径中的文本
call conda info --envs 2>nul | findstr /B /C:"%CONDA_ENV_NAME%" >nul 2>&1
if %ERRORLEVEL% == 0 (
    echo [INFO] 检测到命名环境: %CONDA_ENV_NAME%
    set "CONDA_ENV_MODE=named"
    goto :env_check_ok
)

REM 检查旧版本路径环境
if exist "%CONDA_ENV_PATH%\python.exe" (
    echo [INFO] 检测到路径环境（旧版本）
    set "CONDA_ENV_MODE=legacy"
    goto :env_check_ok
)

REM 没有任何环境
echo [ERROR] 未检测到Conda环境
echo 请先运行 步骤1-首次安装.bat 创建环境
pause
exit /b 1

:env_check_ok

call :resolve_env_path_s2
if not defined ENV_PATH goto :activate_failed_s2
if not exist "!ENV_PATH!\python.exe" goto :activate_failed_s2
set "ENV_PYTHON=!ENV_PATH!\python.exe"
set "USE_DIRECT_ENV_PYTHON=0"

if /I "!CONDA_ENV_MODE!"=="named" (
    REM 方法1: 优先激活命名环境
    call conda activate "%CONDA_ENV_NAME%" 2>nul && goto :activated_ok_s2

    REM 方法2: activate.bat 激活命名环境
    echo [INFO] 尝试备用激活方式...
    if exist "%MINICONDA_ROOT%\Scripts\activate.bat" (
        call "%MINICONDA_ROOT%\Scripts\activate.bat" "%CONDA_ENV_NAME%" 2>nul && goto :activated_ok_s2
    )
) else (
    REM 方法1: 优先按路径激活旧版本环境
    call conda activate "!ENV_PATH!" 2>nul && goto :activated_ok_s2

    REM 方法2: activate.bat 按路径激活旧版本环境
    echo [INFO] 尝试备用激活方式...
    if exist "%MINICONDA_ROOT%\Scripts\activate.bat" (
        call "%MINICONDA_ROOT%\Scripts\activate.bat" "!ENV_PATH!" 2>nul && goto :activated_ok_s2
    )
)

echo [WARNING] 环境激活失败，回退到直接调用环境 Python
echo [INFO] 环境路径: !ENV_PATH!
call :apply_env_runtime_path_s2
set "USE_DIRECT_ENV_PYTHON=1"
set "CONDA_PREFIX=!ENV_PATH!"
if /I "!CONDA_ENV_MODE!"=="named" (
    set "CONDA_DEFAULT_ENV=%CONDA_ENV_NAME%"
) else (
    set "CONDA_DEFAULT_ENV=!ENV_PATH!"
)
goto :activated_ok_s2

:activate_failed_s2
echo [ERROR] 无法激活环境
echo 请尝试: 打开新命令提示符，运行 conda init cmd.exe，然后重试
pause
exit /b 1

:resolve_env_path_s2
set "ENV_PATH="
if exist "%MINICONDA_ROOT%\envs\%CONDA_ENV_NAME%\python.exe" set "ENV_PATH=%MINICONDA_ROOT%\envs\%CONDA_ENV_NAME%"
if not defined ENV_PATH (
    for /f "tokens=1,2,3" %%a in ('conda info --envs 2^>nul ^| findstr /B /C:"%CONDA_ENV_NAME%"') do (
        if "%%b"=="*" (
            set "ENV_PATH=%%c"
        ) else (
            set "ENV_PATH=%%b"
        )
    )
)
if not defined ENV_PATH if exist "%CONDA_ENV_PATH%\python.exe" set "ENV_PATH=%CONDA_ENV_PATH%"
exit /b 0

:apply_env_runtime_path_s2
set "PATH=!ENV_PATH!;!ENV_PATH!\Library\mingw-w64\bin;!ENV_PATH!\Library\usr\bin;!ENV_PATH!\Library\bin;!ENV_PATH!\Scripts;!ENV_PATH!\bin;%PATH%"
exit /b 0

:run_env_python_s2
if "%USE_DIRECT_ENV_PYTHON%"=="1" (
    call "!ENV_PYTHON!" %*
) else (
    call python %*
)
exit /b %ERRORLEVEL%

:activated_ok_s2

REM 检查是否有便携版 Git
if not exist "PortableGit\cmd\git.exe" goto :skip_git_s2
set "PATH=%SCRIPT_DIR%\PortableGit\cmd;%PATH%"
:skip_git_s2

REM 切换到项目根目录(确保Python能正确找到模块)
cd /d "%~dp0"

REM 直接启动 Qt 界面
call :run_env_python_s2 desktop_qt_ui\main.py
pause
goto :eof

:detect_conda_registry_s2
set "CONDA_REGISTRY_FOUND=0"
reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall" /f "Miniconda" /s >nul 2>&1 && set "CONDA_REGISTRY_FOUND=1"
if "!CONDA_REGISTRY_FOUND!"=="0" reg query "HKLM\Software\Microsoft\Windows\CurrentVersion\Uninstall" /f "Miniconda" /s >nul 2>&1 && set "CONDA_REGISTRY_FOUND=1"
if "!CONDA_REGISTRY_FOUND!"=="0" reg query "HKLM\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall" /f "Miniconda" /s >nul 2>&1 && set "CONDA_REGISTRY_FOUND=1"
if "!CONDA_REGISTRY_FOUND!"=="0" reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall" /f "Anaconda" /s >nul 2>&1 && set "CONDA_REGISTRY_FOUND=1"
if "!CONDA_REGISTRY_FOUND!"=="0" reg query "HKLM\Software\Microsoft\Windows\CurrentVersion\Uninstall" /f "Anaconda" /s >nul 2>&1 && set "CONDA_REGISTRY_FOUND=1"
if "!CONDA_REGISTRY_FOUND!"=="0" reg query "HKLM\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall" /f "Anaconda" /s >nul 2>&1 && set "CONDA_REGISTRY_FOUND=1"
if "!CONDA_REGISTRY_FOUND!"=="0" reg query "HKCU\Software\Microsoft\Command Processor" /v AutoRun 2>nul | findstr /I "conda" >nul 2>&1 && set "CONDA_REGISTRY_FOUND=1"
if "!CONDA_REGISTRY_FOUND!"=="0" reg query "HKLM\Software\Microsoft\Command Processor" /v AutoRun 2>nul | findstr /I "conda" >nul 2>&1 && set "CONDA_REGISTRY_FOUND=1"
goto :eof

:report_conda_registry_status_s2
if "!CONDA_REGISTRY_FOUND!"=="1" (
    echo [INFO] 检测到注册表安装信息
) else (
    if defined MINICONDA_ROOT (
        echo [INFO] 未检测到注册表信息，但已检测到可用 Conda
    ) else (
        echo [INFO] 未检测到注册表安装信息
    )
)
goto :eof

:validate_conda_root_s2
set "CONDA_VALID=0"
set "CONDA_VALID_BASE="
if not defined MINICONDA_ROOT goto :eof
if exist "%MINICONDA_ROOT%\condabin\conda.bat" (
    set "PATH=%MINICONDA_ROOT%\condabin;%MINICONDA_ROOT%\Scripts;%PATH%"
) else if exist "%MINICONDA_ROOT%\Scripts\conda.exe" (
    set "PATH=%MINICONDA_ROOT%\Scripts;%PATH%"
) else (
    goto :eof
)
if exist "%MINICONDA_ROOT%\Scripts\conda.exe" (
    call "%MINICONDA_ROOT%\Scripts\conda.exe" --version >nul 2>&1
    if errorlevel 1 goto :eof
    for /f "delims=" %%i in ('"%MINICONDA_ROOT%\Scripts\conda.exe" info --base 2^>nul') do set "CONDA_VALID_BASE=%%i"
) else (
    call conda --version >nul 2>&1
    if errorlevel 1 goto :eof
    for /f "delims=" %%i in ('conda info --base 2^>nul') do set "CONDA_VALID_BASE=%%i"
)
if not defined CONDA_VALID_BASE goto :eof
if not exist "!CONDA_VALID_BASE!\Scripts\conda.exe" goto :eof
set "MINICONDA_ROOT=!CONDA_VALID_BASE!"
set "CONDA_VALID=1"
goto :eof
