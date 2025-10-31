@echo off
chcp 936 >nul
setlocal EnableDelayedExpansion

echo.
echo ========================================
echo 漫画翻译器 - 一键安装程序
echo Manga Translator UI - Installer
echo ========================================
echo.
echo 本脚本将自动完成以下步骤:
echo [1] 检查 Python 3.12+
echo [2] 下载便携版 Git (如需要)
echo [3] 从 GitHub 克隆代码
echo [4] 安装 Python 依赖
echo [5] 完成安装
echo.
pause

REM ===== 步骤1: 检查Python =====
echo.
echo [1/5] 检查 Python 3.12...
echo ========================================

py -3.12 --version >nul 2>&1
if %ERRORLEVEL% == 0 (
    set PYTHON=py -3.12
    echo [OK] 找到 Python 3.12
    goto :check_git
)

python --version >nul 2>&1
if %ERRORLEVEL% == 0 (
    python --version | findstr "3\.12\." >nul
    if %ERRORLEVEL% == 0 (
        set PYTHON=python
        echo [OK] 找到 Python 3.12
        goto :check_git
    ) else (
        REM 检查是否是更高版本
        python --version | findstr "3\.1[3-9]\." >nul
        if %ERRORLEVEL% == 0 (
            echo.
            echo [ERROR] 错误: 检测到 Python 3.13+ 版本
            echo.
            echo 本项目仅支持 Python 3.12,不支持更高版本
            echo 请安装 Python 3.12 版本:
            echo https://www.python.org/downloads/release/python-3120/
            echo.
            pause
            exit /b 1
        )
    )
)

echo.
echo [ERROR] 错误: 未找到 Python 3.12
echo.
echo 本项目仅支持 Python 3.12 版本
echo 请先安装 Python 3.12:
echo https://www.python.org/downloads/release/python-3120/
echo.
echo 安装时请勾选 "Add Python to PATH"
echo.
pause
exit /b 1

REM ===== 步骤2: 检查/下载Git =====
:check_git
echo.
echo [2/5] 检查 Git...
echo ========================================

git --version >nul 2>&1
if %ERRORLEVEL% == 0 (
    set GIT=git
    echo [OK] 找到系统Git
    goto :clone_repo
)

echo [INFO] 未找到 Git
echo.
echo Git是代码拉取必需的,请选择:
echo [1] 下载便携版 Git (推荐, 约50MB)
echo [2] 退出,手动安装 Git
echo.
set /p git_choice="请选择 (1/2): "

if "%git_choice%"=="2" (
    echo.
    echo 下载地址: https://git-scm.com/downloads
    pause
    exit /b 0
)

if not "%git_choice%"=="1" (
    echo 无效选项
    goto :check_git
)

REM 下载Git
echo.
echo 正在下载 Git 便携版...
echo.
echo 请选择下载源:
echo [1] GitHub 官方
echo [2] gitproxy.click 镜像 (国内快)
echo.
set /p git_source="请选择 (1/2, 默认2): "

set GIT_VERSION=2.43.0
set GIT_ARCH=64-bit

if "%git_source%"=="1" (
    set GIT_URL=https://github.com/git-for-windows/git/releases/download/v%GIT_VERSION%.windows.1/PortableGit-%GIT_VERSION%-%GIT_ARCH%.7z.exe
    echo 使用: GitHub 官方源
) else (
    set GIT_URL=https://gitproxy.click/https://github.com/git-for-windows/git/releases/download/v%GIT_VERSION%.windows.1/PortableGit-%GIT_VERSION%-%GIT_ARCH%.7z.exe
    echo 使用: gitproxy.click 镜像
)

echo.
echo 下载中... (约50MB, 可能需要几分钟)
if not exist "tmp" mkdir tmp
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $ProgressPreference = 'SilentlyContinue'; Write-Host '正在下载...'; try { Invoke-WebRequest -Uri '%GIT_URL%' -OutFile 'tmp\PortableGit.7z.exe' -UseBasicParsing; Write-Host '[OK] 下载完成'; exit 0 } catch { Write-Host '[ERROR] 下载失败: $_'; exit 1 }}"

if %ERRORLEVEL% neq 0 (
    echo.
    echo 下载失败,请检查网络连接后重试
    pause
    exit /b 1
)

echo.
echo 正在解压 Git...
tmp\PortableGit.7z.exe -o"PortableGit" -y >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo 解压失败
    pause
    exit /b 1
)

del tmp\PortableGit.7z.exe >nul 2>&1
set GIT=PortableGit\cmd\git.exe
set "PATH=%CD%\PortableGit\cmd;%PATH%"
echo [OK] Git 安装完成
PortableGit\cmd\git.exe --version

REM ===== 步骤3: 克隆/更新仓库 =====
:clone_repo
echo.
echo [3/5] 检查代码仓库...
echo ========================================
echo.

REM 先获取目标仓库地址
call :get_repo_url

REM 检查是否已存在代码仓库
if exist ".git" (
    echo [INFO] 检测到现有Git仓库
    
    REM 获取当前仓库地址
    for /f "delims=" %%i in ('%GIT% config --get remote.origin.url 2^>nul') do set CURRENT_REPO=%%i
    
    if defined CURRENT_REPO (
        echo 当前仓库: !CURRENT_REPO!
        echo 目标仓库: !REPO_URL!
        echo.
        
        REM 标准化仓库地址进行比较
        set CURRENT_CLEAN=!CURRENT_REPO:.git=!
        set TARGET_CLEAN=!REPO_URL:.git=!
        set CURRENT_CLEAN=!CURRENT_CLEAN:https://gitproxy.click/https://github.com/=https://github.com/!
        set TARGET_CLEAN=!TARGET_CLEAN:https://gitproxy.click/https://github.com/=https://github.com/!
        
        if "!CURRENT_CLEAN!"=="!TARGET_CLEAN!" (
            echo [OK] 仓库地址匹配,正在强制同步到最新版本...
            echo.
            
            echo 获取远程更新...
            %GIT% fetch origin
            if !ERRORLEVEL! neq 0 (
                echo [WARNING] 获取更新失败,可能是网络问题
            ) else (
                echo 强制同步到远程主分支...
                %GIT% reset --hard origin/main
                if !ERRORLEVEL! == 0 (
                    echo [OK] 代码已更新到最新版本
                    echo.
                    goto :create_venv
                ) else (
                    echo [WARNING] 同步失败,尝试使用 main 分支...
                    %GIT% checkout -f main
                    %GIT% reset --hard origin/main
                    if !ERRORLEVEL! == 0 (
                        echo [OK] 代码已更新到最新版本
                        echo.
                        goto :create_venv
                    )
                )
            )
            
            echo [WARNING] 自动更新失败,将删除并重新克隆
            echo.
        ) else (
            echo [警告] 仓库地址不匹配
            echo.
            echo 请选择:
            echo [1] 删除现有仓库并克隆新仓库
            echo [2] 保留现有仓库,跳过克隆
            echo [3] 退出安装
            echo.
            set /p mismatch_choice="请选择 (1/2/3): "
            
            if "!mismatch_choice!"=="2" (
                echo [INFO] 保留现有仓库
                goto :create_venv
            ) else if "!mismatch_choice!"=="3" (
                exit /b 0
            )
            
            echo 正在删除现有仓库...
        )
    ) else (
        echo [WARNING] 无法读取仓库信息,将重新克隆
    )
    
    REM 删除现有文件和目录(保留venv和PortableGit)
    echo 正在清理旧文件...
    
    REM 删除目录(保留venv和PortableGit)
    for /d %%d in (*) do (
        if /i not "%%d"=="venv" if /i not "%%d"=="PortableGit" (
            echo 删除目录: %%d
            rmdir /s /q "%%d" 2>nul
        )
    )
    
    REM 删除文件(保留当前运行的脚本)
    for %%f in (*) do (
        if /i not "%%~nxf"=="步骤1-首次安装.bat" (
            echo 删除文件: %%~nxf
            del /f /q "%%f" 2>nul
        )
    )
    
    REM 删除隐藏的.git目录
    if exist ".git" (
        echo 删除 .git 目录...
        rmdir /s /q ".git" 2>nul
        if exist ".git" (
            echo [ERROR] 无法删除 .git 目录,可能被占用
            echo 请关闭所有相关程序后重试
            pause
            exit /b 1
        )
    )
    
    echo [OK] 已清理旧数据
    echo.
)

echo 仓库地址: !REPO_URL!
echo 安装目录: %CD%
echo.
goto :do_clone

:get_repo_url
echo 请选择克隆源:
echo [1] GitHub 官方
echo [2] gitproxy.click 镜像 (国内快)
echo [3] 手动输入仓库地址
echo.
set /p repo_choice="请选择 (1/2/3, 默认1): "

if "%repo_choice%"=="2" (
    set REPO_URL=https://gitproxy.click/https://github.com/hgmzhn/manga-translator-ui.git
    echo 使用: gitproxy.click镜像
) else if "%repo_choice%"=="3" (
    set /p REPO_URL="请输入仓库地址: "
    echo 使用: 自定义地址
) else (
    set REPO_URL=https://github.com/hgmzhn/manga-translator-ui.git
    echo 使用: GitHub官方
)
echo.
goto :eof

:do_clone

REM 使用临时目录克隆
set TEMP_DIR=manga_translator_temp_%RANDOM%
echo 正在克隆代码到临时目录... (可能需要几分钟)
echo.
%GIT% clone !REPO_URL! %TEMP_DIR%

echo.
echo [DEBUG] 检查克隆结果...
echo [DEBUG] 临时目录: %TEMP_DIR%
echo [DEBUG] 完整路径: %CD%\%TEMP_DIR%
if exist "%TEMP_DIR%" (
    echo [DEBUG] 临时目录存在
    if exist "%TEMP_DIR%\.git" (
        echo [DEBUG] .git 目录存在 - 克隆成功!
        goto :copy_files
    ) else (
        echo [DEBUG] .git 目录不存在 - 克隆失败!
    )
) else (
    echo [DEBUG] 临时目录不存在 - 克隆失败!
)

REM 如果到这里说明克隆失败
echo.
echo [ERROR] 克隆失败
echo.
echo 可能原因:
echo 1. 网络连接问题
echo 2. 仓库地址错误
echo 3. GitHub访问受限 (请选择GHProxy镜像重试)
echo.
if exist "%TEMP_DIR%" rmdir /s /q "%TEMP_DIR%"
set /p retry="是否重试? (y/n): "
if /i "!retry!"=="y" goto :clone_repo
pause
exit /b 1

:copy_files

echo.
echo [DEBUG] 开始复制文件...
echo [DEBUG] 临时目录: %TEMP_DIR%
echo [DEBUG] 当前目录: %CD%
echo.

echo 正在复制目录...
for /d %%i in ("%TEMP_DIR%\*") do (
    if /i not "%%~nxi"=="PortableGit" (
        echo [DEBUG] 复制目录: %%~nxi
        xcopy "%%i" "%CD%\%%~nxi\" /E /H /Y /I /Q
        if !ERRORLEVEL! neq 0 echo [ERROR] 复制目录失败: %%~nxi (错误码: !ERRORLEVEL!)
    )
)

echo.
echo 正在复制文件...
for %%i in ("%TEMP_DIR%\*") do (
    if /i not "%%~nxi"=="步骤1-首次安装.bat" (
        echo [DEBUG] 复制文件: %%~nxi
        copy /Y "%%i" "%CD%\"
        if !ERRORLEVEL! neq 0 echo [ERROR] 复制文件失败: %%~nxi (错误码: !ERRORLEVEL!)
    )
)

echo.
echo 正在复制隐藏文件...
if exist "%TEMP_DIR%\.git\" (
    echo [DEBUG] 复制 .git 目录...
    xcopy "%TEMP_DIR%\.git" ".git\" /E /H /Y /I /Q
    if !ERRORLEVEL! neq 0 echo [ERROR] 复制.git失败 (错误码: !ERRORLEVEL!)
) else (
    echo [DEBUG] .git 目录不存在
)

if exist "%TEMP_DIR%\.gitignore" (
    echo [DEBUG] 复制 .gitignore 文件...
    copy /Y "%TEMP_DIR%\.gitignore" .
    if !ERRORLEVEL! neq 0 echo [ERROR] 复制.gitignore失败 (错误码: !ERRORLEVEL!)
) else (
    echo [DEBUG] .gitignore 文件不存在
)

echo.
echo [DEBUG] 复制完成，准备清理临时目录...
echo 正在清理临时目录...
rmdir /s /q "%TEMP_DIR%"
if !ERRORLEVEL! neq 0 (
    echo [ERROR] 清理临时目录失败 (错误码: !ERRORLEVEL!)
) else (
    echo [DEBUG] 临时目录已清理
)

echo.
echo [OK] 代码克隆完成

:create_venv

REM ===== 步骤4: 创建虚拟环境并安装依赖 =====
echo.
echo [4/5] 创建虚拟环境并安装依赖...
echo ========================================
echo.

REM 检测虚拟环境有效性
set VENV_VALID=0
if exist "venv\Scripts\python.exe" (
    echo 检测到现有虚拟环境,正在验证...
    venv\Scripts\python.exe -c "import sys; sys.exit(0)" >nul 2>&1
    if !ERRORLEVEL! == 0 (
        set VENV_VALID=1
        echo [OK] 虚拟环境有效
    ) else (
        echo [警告] 虚拟环境已损坏或失效
    )
)

REM 创建或重建虚拟环境
if !VENV_VALID! == 0 (
    if exist "venv" (
        echo 正在删除无效的虚拟环境...
        rmdir /s /q "venv" 2>nul
        if exist "venv" (
            echo [ERROR] 无法删除旧的虚拟环境
            echo 请手动删除 venv 文件夹后重试
            pause
            exit /b 1
        )
    )
    
    echo 正在创建虚拟环境...
    %PYTHON% -m venv venv
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] 虚拟环境创建失败
        pause
        exit /b 1
    )
    echo [OK] 虚拟环境创建完成
)

echo.
echo 正在激活虚拟环境...
call venv\Scripts\activate.bat

echo 正在升级 pip...
python -m pip install --upgrade pip >nul 2>&1

echo 正在安装基础依赖...
python -m pip install packaging setuptools wheel >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [WARNING] 基础依赖安装失败,继续尝试...
)

echo 正在检测 GPU 支持...
echo.

REM 调用项目的 launch.py 进行依赖安装
python launch.py --install-deps-only

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] 依赖安装失败
    echo.
    echo 你可以稍后手动运行:
    echo   步骤3-更新维护.bat
    echo.
    pause
    exit /b 1
)

echo.
echo [OK] 依赖安装完成

REM ===== 步骤5: 完成 =====
echo.
echo [5/5] 安装完成!
echo ========================================
echo.
echo [OK] 所有步骤已完成!
echo.
echo 安装位置: %CD%
echo.
echo 下一步操作:
echo   双击 步骤2-启动Qt界面.bat (Qt版本)
echo.
echo 定期更新:
echo   双击 步骤3-更新维护.bat
echo.
pause

REM 询问是否立即运行
set /p run_now="是否立即运行? (y/n): "
if /i "%run_now%"=="y" (
    echo.
    echo 正在启动...
    start 步骤2-启动Qt界面.bat
)

echo.
echo 安装流程已结束
pause
