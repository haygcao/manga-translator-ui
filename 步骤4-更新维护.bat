@echo off
chcp 936 >nul
setlocal EnableDelayedExpansion

REM 设置 PYTHONUTF8=1 避免conda编码错误
set "PYTHONUTF8=1"

echo.
echo ========================================
echo 漫画翻译器 - 更新维护工具
echo Manga Translator UI - Update Tool
echo ========================================
echo.

REM 修复管理员模式下%CD%变成system32的问题
REM 使用脚本所在目录作为工作目录
cd /d "%~dp0"
set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

REM 检查conda环境（兼容命名环境和路径环境）
set CONDA_ENV_NAME=manga-env
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

REM 先检查系统conda
where conda >nul 2>&1
if %ERRORLEVEL% neq 0 goto :check_local_conda_s4

REM 检测到系统conda，获取实际路径
REM 方法1: 从CONDA_EXE环境变量获取（最可靠）
if defined CONDA_EXE (
    for %%p in ("%CONDA_EXE%\..\..") do set "MINICONDA_ROOT=%%~fp"
)

REM 方法2: 从CONDA_PREFIX环境变量获取
if "!MINICONDA_ROOT!"=="" (
    if defined CONDA_PREFIX (
        set "MINICONDA_ROOT=%CONDA_PREFIX%"
    )
)

REM 方法3: 使用 conda info --base
if "!MINICONDA_ROOT!"=="" (
    for /f "delims=" %%i in ('conda info --base 2^>nul') do (
        set "TEMP_PATH=%%i"
        if exist "!TEMP_PATH!\Scripts\conda.exe" (
            set "MINICONDA_ROOT=%%i"
        )
    )
)

REM 方法4: 从 where conda 解析路径
if "!MINICONDA_ROOT!"=="" (
    for /f "delims=" %%i in ('where conda 2^>nul') do (
        if "!MINICONDA_ROOT!"=="" (
            if "%%~xi"==".exe" (
                for %%p in ("%%~dpi..") do set "MINICONDA_ROOT=%%~fp"
            ) else if "%%~xi"==".bat" (
                for %%p in ("%%~dpi..\..") do set "MINICONDA_ROOT=%%~fp"
            )
        )
    )
)

goto :check_env_s4

:check_local_conda_s4
REM 检查本地Miniconda（优先脚本目录）
if exist "%SCRIPT_DIR%\Miniconda3\Scripts\conda.exe" (
    set MINICONDA_ROOT=%SCRIPT_DIR%\Miniconda3
    echo [INFO] 检测到本地 Miniconda: %MINICONDA_ROOT%
    call "%MINICONDA_ROOT%\Scripts\activate.bat"
    goto :check_env_s4
)

REM 检查磁盘根目录
if exist "%~d0\Miniconda3\Scripts\conda.exe" (
    set MINICONDA_ROOT=%~d0\Miniconda3
    echo [INFO] 检测到本地 Miniconda: %MINICONDA_ROOT%
    call "%MINICONDA_ROOT%\Scripts\activate.bat"
    goto :check_env_s4
)

echo [ERROR] 未检测到 Conda
echo 请先运行 步骤1-首次安装.bat 安装 Miniconda
pause
exit /b 1

:check_env_s4

REM 检查环境是否存在（优先检查命名环境）
set ENV_FOUND=0

REM 方法1: 检查命名环境
REM 使用 /B 选项进行精确匹配行首，避免误匹配路径中的文本
call conda info --envs 2>nul | findstr /B /C:"%CONDA_ENV_NAME%" >nul 2>&1
if %ERRORLEVEL% == 0 (
    set ENV_FOUND=1
    set USE_NAMED_ENV=1
    echo [INFO] 检测到命名环境: %CONDA_ENV_NAME%
)

REM 方法2: 检查旧版本路径环境
if %ENV_FOUND% == 0 (
    if exist "%CONDA_ENV_PATH%\python.exe" (
        set ENV_FOUND=1
        set USE_NAMED_ENV=0
        echo [INFO] 检测到路径环境（旧版本）: %CONDA_ENV_PATH%
    )
)

REM 如果两种环境都不存在
if %ENV_FOUND% == 0 (
    echo [ERROR] 未检测到Conda环境
    echo 请先运行 步骤1-首次安装.bat 创建环境
    pause
    exit /b 1
)

REM 激活conda环境
echo 正在激活环境...
if %USE_NAMED_ENV% == 1 (
    REM 激活命名环境
    call conda activate "%CONDA_ENV_NAME%" 2>nul
    if %ERRORLEVEL% == 0 (
        echo [OK] 已激活命名环境: %CONDA_ENV_NAME%
        goto :env_activated
    ) else (
        echo [WARNING] 无法激活命名环境: %CONDA_ENV_NAME%
    )
) else (
    REM 激活路径环境（旧版本）- 使用多层降级策略
    echo [INFO] 尝试激活路径环境（旧版本）...

    REM 方法1: 使用activate.bat
    if exist "%MINICONDA_ROOT%\Scripts\activate.bat" (
        call "%MINICONDA_ROOT%\Scripts\activate.bat" "%CONDA_ENV_PATH%" 2>nul
        if %ERRORLEVEL% == 0 (
            echo [OK] 已激活路径环境（activate.bat方式）
            goto :env_activated
        )
    )

    REM 方法2: 使用conda activate
    call conda activate "%CONDA_ENV_PATH%" 2>nul
    if %ERRORLEVEL% == 0 (
        echo [OK] 已激活路径环境（conda activate方式）
        goto :env_activated
    )

    REM 方法3: 手动设置PATH（兜底方案）
    echo [INFO] 使用手动PATH激活方式...
    set "PATH=%CONDA_ENV_PATH%;%CONDA_ENV_PATH%\Library\mingw-w64\bin;%CONDA_ENV_PATH%\Library\usr\bin;%CONDA_ENV_PATH%\Library\bin;%CONDA_ENV_PATH%\Scripts;%CONDA_ENV_PATH%\bin;%PATH%"
    set "CONDA_PREFIX=%CONDA_ENV_PATH%"
    set "CONDA_DEFAULT_ENV=%CONDA_ENV_PATH%"
    echo [OK] 已使用手动PATH方式激活环境
    goto :env_activated
)

echo [ERROR] 无法激活环境
pause
exit /b 1

:env_activated

REM 检查是否有便携版 Git
if exist "PortableGit\cmd\git.exe" (
    set "GIT=%SCRIPT_DIR%\PortableGit\cmd\git.exe"
    set "PATH=%SCRIPT_DIR%\PortableGit\cmd;%PATH%"
) else (
    git --version >nul 2>&1
    if %ERRORLEVEL% == 0 (
        set GIT=git
    ) else (
        echo [ERROR] 未找到 Git
        echo 请先安装 Git 或运行 步骤1-首次安装.bat
        pause
        exit /b 1
    )
)

REM 检查版本信息 (在菜单显示前) - 使用Python脚本
:check_version
echo.
echo 正在检查版本...
echo ========================================

REM 使用Python脚本检查版本（避免批处理冒号问题）
python packaging\check_version.py

REM 获取版本信息供后续使用
for /f "tokens=1,2 delims==" %%a in ('python packaging\check_version.py --export-vars') do (
    if "%%a"=="CURRENT_VERSION" set CURRENT_VERSION=%%b
    if "%%a"=="REMOTE_VERSION" set REMOTE_VERSION=%%b
)

echo.
echo ========================================

REM 菜单
:menu
echo.
echo 请选择操作:
echo [1] 更新代码 (强制同步)
echo [2] 更新/安装依赖
echo [3] 完整更新 (代码+依赖)
echo [4] 重新检查版本
echo [5] 退出
echo.
set /p choice="请选择 (1/2/3/4/5): "

if "%choice%"=="1" goto update_code
if "%choice%"=="2" goto update_deps
if "%choice%"=="3" goto full_update
if "%choice%"=="4" (
    REM 重新检查版本,需要跳转到脚本开始的版本检查部分
    cls
    echo.
    echo ========================================
    echo 漫画翻译器 - 更新维护工具
    echo Manga Translator UI - Update Tool
    echo ========================================
    goto check_version
)
if "%choice%"=="5" goto end

echo 无效选项
goto menu

:update_code
echo.
echo ========================================
echo 更新代码 (强制同步)
echo ========================================
echo.

echo [警告] 将强制同步到远程分支,本地修改将被覆盖
set /p confirm="是否继续更新? (y/n): "
if /i not "!confirm!"=="y" (
    echo 取消更新
    goto menu
)

echo.
echo 正在强制同步到远程分支...
"%GIT%" reset --hard origin/main

if %ERRORLEVEL% == 0 (
    echo [OK] 代码更新完成
) else (
    echo [ERROR] 代码更新失败
)
pause
goto menu

:update_deps
echo.
echo ========================================
echo 更新/安装依赖
echo ========================================
echo.

REM 检测当前环境的 PyTorch 类型
echo 正在检测 PyTorch 版本类型...
python packaging\detect_torch_type.py >nul 2>&1
if %ERRORLEVEL% == 0 (
    REM 检测成功,获取对应的 requirements 文件
    for /f "delims=" %%i in ('python packaging\detect_torch_type.py --file-only') do set REQ_FILE=%%i
    echo 检测到 PyTorch 类型,使用: !REQ_FILE!
    echo.
    python packaging\launch.py --install-deps-only --update-deps --requirements !REQ_FILE!
) else (
    REM 检测失败(未安装PyTorch),让 launch.py 自动选择
    echo 未检测到 PyTorch,将进行首次安装...
    echo.
    python packaging\launch.py --install-deps-only --update-deps
)

if %ERRORLEVEL% == 0 (
    echo [OK] 依赖更新完成
) else (
    echo [ERROR] 依赖更新失败
)
pause
goto menu

:full_update
echo.
echo ========================================
echo 完整更新 (代码+依赖)
echo ========================================
echo.

echo [1/2] 更新代码 (强制同步)...
echo [警告] 将强制同步到远程分支,本地修改将被覆盖
set /p confirm="是否继续? (y/n): "
if /i not "!confirm!"=="y" (
    echo 取消更新
    goto menu
)

echo.
echo 获取远程更新...
"%GIT%" fetch origin

echo.
echo 正在强制同步到远程分支...
"%GIT%" reset --hard origin/main

if %ERRORLEVEL% neq 0 (
    echo [ERROR] 代码更新失败
    pause
    goto menu
)
echo [OK] 代码更新完成

echo.
echo [2/2] 更新依赖...

REM 检测当前环境的 PyTorch 类型
echo 正在检测 PyTorch 版本类型...
python packaging\detect_torch_type.py >nul 2>&1
if %ERRORLEVEL% == 0 (
    REM 检测成功,获取对应的 requirements 文件
    for /f "delims=" %%i in ('python packaging\detect_torch_type.py --file-only') do set REQ_FILE=%%i
    echo 检测到 PyTorch 类型,使用: !REQ_FILE!
    echo.
    python packaging\launch.py --install-deps-only --update-deps --requirements !REQ_FILE!
) else (
    REM 检测失败(未安装PyTorch),让 launch.py 自动选择
    echo 未检测到 PyTorch,将进行首次安装...
    echo.
    python packaging\launch.py --install-deps-only --update-deps
)

if %ERRORLEVEL% == 0 (
    echo.
    echo [OK] 完整更新完成
) else (
    echo [ERROR] 依赖更新失败
)
pause
goto menu

:end
echo.
echo 退出更新工具
pause
