#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
漫画翻译器启动脚本
Manga Translator UI Launcher
"""

import os
import sys
import argparse
import subprocess
import importlib.util
from pathlib import Path

# 项目配置
BRANCH = 'main'
VERSION = '1.7.6'
PYTHON_VERSION_MIN = (3, 12)
PYTHON_VERSION_MAX = (3, 12)  # 仅支持Python 3.12,不支持3.13+

# 路径配置
PATH_ROOT = Path(__file__).parent.parent
stored_commit_hash = None

# 获取环境变量
python = sys.executable

# Git路径配置 (优先使用便携版)
portable_git = PATH_ROOT / "PortableGit" / "cmd" / "git.exe"
if portable_git.exists():
    git = str(portable_git)
else:
    git = os.environ.get('GIT', "git")

skip_install = False
index_url = os.environ.get('INDEX_URL', "")


def is_python_version_valid():
    """检查Python版本是否符合要求"""
    if sys.version_info < PYTHON_VERSION_MIN:
        print(f'错误: 需要 Python {PYTHON_VERSION_MIN[0]}.{PYTHON_VERSION_MIN[1]}+ ')
        print(f'当前版本: Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')
        return False
    if sys.version_info[:2] > PYTHON_VERSION_MAX:
        print(f'错误: 仅支持 Python {PYTHON_VERSION_MAX[0]}.{PYTHON_VERSION_MAX[1]},不支持更高版本')
        print(f'当前版本: Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')
        print(f'请使用 Python {PYTHON_VERSION_MAX[0]}.{PYTHON_VERSION_MAX[1]} 版本')
        return False
    return True


def is_installed(package):
    """检查Python包是否已安装"""
    try:
        spec = importlib.util.find_spec(package)
    except ModuleNotFoundError:
        return False
    return spec is not None


def run(command, desc=None, errdesc=None, custom_env=None, live=False):
    """执行系统命令"""
    if desc is not None:
        print(desc)

    if live:
        result = subprocess.run(command, shell=True, env=os.environ if custom_env is None else custom_env)
        if result.returncode != 0:
            raise RuntimeError(f"""{errdesc or '命令执行错误'}.
命令: {command}
错误代码: {result.returncode}""")
        return ""

    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True,
                            env=os.environ if custom_env is None else custom_env)

    if result.returncode != 0:
        message = f"""{errdesc or '命令执行错误'}.
命令: {command}
错误代码: {result.returncode}
stdout: {result.stdout.decode(encoding="utf8", errors="ignore") if len(result.stdout) > 0 else '<empty>'}
stderr: {result.stderr.decode(encoding="utf8", errors="ignore") if len(result.stderr) > 0 else '<empty>'}
"""
        raise RuntimeError(message)

    return result.stdout.decode(encoding="utf8", errors="ignore")


def run_pip(args, desc=None):
    """使用pip安装包"""
    if skip_install:
        return
    
    index_url_line = f' --index-url {index_url}' if index_url != '' else ''
    return run(f'"{python}" -m pip {args} --prefer-binary{index_url_line} --disable-pip-version-check --no-warn-script-location',
               desc=f"正在安装 {desc}", errdesc=f"无法安装 {desc}", live=True)


def commit_hash():
    """获取当前Git commit hash"""
    global stored_commit_hash
    if stored_commit_hash is not None:
        return stored_commit_hash

    try:
        stored_commit_hash = run(f"{git} rev-parse HEAD").strip()
    except Exception:
        stored_commit_hash = "<none>"

    return stored_commit_hash


def restart():
    """重启应用"""
    print('正在重启应用...\n')
    os.execv(sys.executable, ['python'] + sys.argv)


def detect_gpu():
    """检测GPU类型"""
    try:
        if sys.platform == 'win32':
            cmd = 'wmic path win32_VideoController get name'
            output = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL)
            
            if any(keyword in output for keyword in ["NVIDIA", "GeForce", "GTX", "RTX", "Quadro"]):
                return "NVIDIA"
            elif any(keyword in output for keyword in ["AMD", "Radeon"]):
                return "AMD"
            elif any(keyword in output for keyword in ["Intel"]):
                return "Intel"
        else:
            # Linux/Mac: 使用lspci或其他工具
            try:
                output = subprocess.check_output("lspci | grep -i vga", shell=True, text=True, stderr=subprocess.DEVNULL)
                if "NVIDIA" in output:
                    return "NVIDIA"
                elif "AMD" in output or "ATI" in output:
                    return "AMD"
                elif "Intel" in output:
                    return "Intel"
            except:
                pass
    except Exception:
        pass
    return "CPU"


def detect_installed_pytorch_version():
    """检测当前安装的PyTorch版本类型(CPU/GPU)"""
    try:
        import torch
        if torch.cuda.is_available():
            # 检查CUDA版本
            cuda_version = torch.version.cuda
            if cuda_version:
                return "GPU", f"CUDA {cuda_version}"
        return "CPU", "CPU-only"
    except (ImportError, AttributeError):
        return None, "未安装"


def get_requirements_file_from_env():
    """从当前虚拟环境检测应该使用哪个requirements文件"""
    pytorch_type, detail = detect_installed_pytorch_version()
    
    if pytorch_type == "GPU":
        return 'requirements_gpu.txt', pytorch_type, detail
    elif pytorch_type == "CPU":
        return 'requirements_cpu.txt', pytorch_type, detail
    else:
        # 未安装PyTorch,返回None让后续逻辑自动检测
        return None, None, detail


def prepare_environment(args):
    """准备运行环境"""
    
    if args.frozen:
        print('frozen模式: 跳过依赖安装')
        return

    # 确保 packaging 已安装 (需要 < 25.0 版本)
    try:
        import packaging
        import packaging.version
        import packaging.utils
        # 检查是否有 packaging.requirements (在 25.0 中已移除)
        try:
            from packaging.requirements import Requirement
        except (ImportError, AttributeError):
            # packaging 版本过高,需要降级
            print('检测到 packaging 版本不兼容,正在安装兼容版本...')
            run_pip("install 'packaging<25.0'", "packaging")
            import packaging
            import packaging.version
            import packaging.utils
            print('✓ packaging 安装成功')
    except (ModuleNotFoundError, ImportError):
        print('正在安装 packaging 模块...')
        run_pip("install 'packaging<25.0'", "packaging")
        try:
            import packaging
            import packaging.version
            import packaging.utils
            print('✓ packaging 安装成功')
        except (ModuleNotFoundError, ImportError):
            print('✗ 警告: packaging 安装失败')

    print('\n正在检查依赖...\n')
    
    # 将项目根目录添加到 Python 路径，以便导入 build_utils
    if str(PATH_ROOT) not in sys.path:
        sys.path.insert(0, str(PATH_ROOT))
    
    # 导入依赖检查工具
    try:
        from build_utils.package_checker import check_req_file
        print('✓ 依赖检查工具加载成功')
    except ImportError as e:
        print(f'✗ 警告: 无法导入依赖检查工具')
        print(f'   原因: {e}')
        print('   将跳过增量检查,强制重新安装所有依赖')
        check_req_file = lambda x: False

    # 检测GPU并选择对应的依赖文件
    gpu_type = detect_gpu()
    print(f'\n检测到的计算设备: {gpu_type}\n')
    # 根据GPU类型选择requirements文件
    if args.requirements != 'auto':
        # 用户手动指定,尊重用户选择
        requirements_file = args.requirements
    else:
        # 自动选择
        if gpu_type == "NVIDIA":
            print('=' * 50)
            print('检测到 NVIDIA GPU')
            print('=' * 50)
            print('')
            print('GPU 版本需要:')
            print('  - NVIDIA 显卡支持 CUDA 12.x')
            print('  - 显卡驱动版本 >= 525.60.13')
            print('')
            print('如果不确定,可以选择 CPU 版本(速度较慢但兼容性好)')
            print('')
            
            while True:
                choice = input('使用 GPU 版本? (y/n, 默认y): ').strip().lower()
                if choice in ['', 'y', 'yes']:
                    requirements_file = 'requirements_gpu.txt'
                    print(f'✓ 使用: {requirements_file} (NVIDIA CUDA)')
                    break
                elif choice in ['n', 'no']:
                    requirements_file = 'requirements_cpu.txt'
                    print(f'✓ 使用: {requirements_file} (CPU版本)')
                    break
                else:
                    print('无效输入,请输入 y 或 n')
        else:
            # AMD GPU 在 Windows 上支持有限,默认使用 CPU 版本
            requirements_file = 'requirements_cpu.txt'
            if gpu_type == "AMD":
                print('检测到 AMD GPU,但Windows上推荐使用CPU版本')
            print(f'自动选择: {requirements_file}')
    
    # 选择对应的PyTorch版本 (根据requirements_gpu.txt中的版本)
    # 注意: 不再单独安装 PyTorch，而是通过 requirements 文件统一安装
    # 这样可以避免版本冲突和 DLL 损坏问题
    
    # 检查是否需要卸载不匹配的 PyTorch 版本
    need_reinstall = args.reinstall_torch
    
    if not need_reinstall:
        # 检测当前安装的 PyTorch 类型
        installed_pytorch_type, installed_detail = detect_installed_pytorch_version()
        target_type = "GPU" if "gpu" in requirements_file.lower() else "CPU"
        
        if installed_pytorch_type is not None and installed_pytorch_type != target_type:
            print('\n' + '=' * 50)
            print('⚠️  警告: 检测到 PyTorch 版本不匹配')
            print('=' * 50)
            print(f'当前安装: {installed_pytorch_type} 版本 ({installed_detail})')
            print(f'目标版本: {target_type} 版本')
            print('')
            print('不同版本的 PyTorch 会导致 DLL 冲突和加载失败')
            print('建议卸载旧版本后重新安装')
            print('')
            need_reinstall = True
    
    # 如果需要重装 PyTorch，先卸载
    if need_reinstall:
        print('正在卸载现有的 PyTorch...')
        run(f'"{python}" -m pip uninstall torch torchvision torchaudio -y', "卸载 PyTorch", "无法卸载 PyTorch", live=True)
        # 强制清理 pip 缓存，避免使用缓存的错误版本
        print('正在清理 pip 缓存...')
        run(f'"{python}" -m pip cache purge', "清理缓存", "无法清理缓存")

    # 检查并安装其他依赖
    if not os.path.exists(requirements_file):
        print(f'警告: 未找到 {requirements_file}')
        return

    print(f'正在检查依赖: {requirements_file}')
    if not check_req_file(requirements_file) or need_reinstall:
        if need_reinstall:
            print(f'强制重新安装所有依赖...')
        else:
            print(f'发现缺失依赖,正在安装...')
        run_pip(f"install -r {requirements_file}", f"{requirements_file} 中的依赖")
    else:
        print(f'依赖已满足 ✓')


def update_repository(args):
    """更新代码库"""
    if getattr(sys, 'frozen', False):
        print('打包版本,跳过更新检查')
        return False

    if not args.update:
        return False

    print('正在检查更新...')
    try:
        current_commit = commit_hash()
        run(f"{git} fetch origin {BRANCH}", desc="正在从远程拉取更新...", errdesc="拉取更新失败")
        latest_commit = run(f"{git} rev-parse origin/{BRANCH}").strip()

        if current_commit != latest_commit:
            print("发现新版本,正在更新...")
            run(f"{git} pull origin {BRANCH}", desc="正在更新代码库...", errdesc="更新失败")
            print("更新完成,正在重启应用...")
            restart()
            return True
        else:
            print("已是最新版本")
    except Exception as e:
        print(f"更新检查失败: {e}")
        print("继续使用当前版本")
    
    return False


def launch_ui(args):
    """启动UI界面"""
    if args.ui == 'qt':
        # 新版 Qt UI (推荐)
        from desktop_qt_ui.main import main as qt_main
        qt_main()
    elif args.ui == 'customtkinter':
        # 旧版 CustomTkinter UI
        import importlib
        desktop_ui = importlib.import_module('desktop-ui.main')
        desktop_ui.main_ui()
    else:
        # 默认使用新版 Qt UI
        from desktop_qt_ui.main import main as qt_main
        qt_main()


def launch_cli(args):
    """启动命令行版本"""
    import manga_translator.__main__ as cli_main
    # 传递参数给命令行版本
    cli_main.main()


def main():
    """主函数"""
    # 检查Python版本
    if not is_python_version_valid():
        sys.exit(1)

    # 解析命令行参数
    parser = argparse.ArgumentParser(description='漫画翻译器启动脚本')
    parser.add_argument("--update", action='store_true', help="启动前检查并自动更新")
    parser.add_argument("--frozen", action='store_true', help="跳过依赖检查(打包版本)")
    parser.add_argument("--install-deps-only", action='store_true', help="仅安装依赖,不启动UI")
    parser.add_argument("--reinstall-torch", action='store_true', help="重新安装PyTorch")
    parser.add_argument("--requirements", default='auto', help="依赖文件路径 (auto=自动选择, 或指定 requirements_gpu.txt/requirements_cpu.txt)")
    parser.add_argument("--ui", choices=['qt', 'tk'], default='tk', help="选择UI框架: qt(PyQt6) 或 tk(CustomTkinter)")
    parser.add_argument("--cli", action='store_true', help="使用命令行模式")
    parser.add_argument("--verbose", action='store_true', help="显示详细日志")
    
    args, unknown = parser.parse_known_args()

    # 显示版本信息
    commit = commit_hash()
    print('=' * 60)
    print('漫画翻译器 Manga Translator UI')
    print('=' * 60)
    print(f'版本: {VERSION}')
    print(f'分支: {BRANCH}')
    print(f'提交: {commit[:8]}')
    print(f'Python: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')
    print(f'Python路径: {sys.executable}')
    print('=' * 60)

    # 切换到项目根目录 (launch.py 在 packaging/ 下,需要切换到父目录)
    APP_DIR = PATH_ROOT
    os.chdir(APP_DIR)

    # 更新检查
    if update_repository(args):
        return  # 更新后会自动重启

    # 准备环境
    print('\n正在检查依赖...')
    prepare_environment(args)

    # 如果只是安装依赖,则退出
    if args.install_deps_only:
        print('\n依赖安装完成!')
        return

    # 启动应用
    print('\n正在启动应用...\n')
    try:
        if args.cli:
            launch_cli(args)
        else:
            launch_ui(args)
    except KeyboardInterrupt:
        print('\n\n用户取消')
        sys.exit(0)
    except Exception as e:
        print(f'\n错误: {e}')
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

