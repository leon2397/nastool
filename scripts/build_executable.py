#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NASTool V4.1 打包脚本
使用 PyInstaller 打包成可执行文件
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent

# 输出目录
OUTPUT_DIR = PROJECT_ROOT / "dist"

# 清理输出目录
def clean_output():
    """清理输出目录"""
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(exist_ok=True)
    print(f"清理并创建输出目录: {OUTPUT_DIR}")

# 安装依赖
def install_dependencies():
    """安装依赖"""
    print("安装依赖...")
    # 安装主要依赖
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", "./nastool-cli"],
        cwd=PROJECT_ROOT,
        check=True
    )
    # 安装其他组件
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", "./nastool-core"],
        cwd=PROJECT_ROOT,
        check=True
    )
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", "./nastool-adapters"],
        cwd=PROJECT_ROOT,
        check=True
    )
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", "./nastool-common"],
        cwd=PROJECT_ROOT,
        check=True
    )
    # 安装PyInstaller
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "pyinstaller"],
        cwd=PROJECT_ROOT,
        check=True
    )

# 打包主可执行文件
def build_main_executable():
    """打包主可执行文件"""
    print("打包主可执行文件...")
    # PyInstaller命令
    cmd = [
        "pyinstaller",
        "--name", "nastool",
        "--onefile",
        "--console",
        "--clean",
        "--paths", f"{PROJECT_ROOT}",
        "--paths", f"{PROJECT_ROOT}/nastool-cli",
        "--paths", f"{PROJECT_ROOT}/nastool-core",
        "--paths", f"{PROJECT_ROOT}/nastool-common",
        "--paths", f"{PROJECT_ROOT}/nastool-adapters",
        "--paths", f"{PROJECT_ROOT}/nastool-fixes",
        "--paths", f"{PROJECT_ROOT}/nastool-reporters",
        "--add-data", f"{PROJECT_ROOT}/nastool-core/nastool_core/data;nastool_core/data",
        "--add-data", f"{PROJECT_ROOT}/nastool-core/create_default_config.py;.",
        "--hidden-import", "nastool_common",
        "--hidden-import", "nastool_core",
        "--hidden-import", "nastool_reporters",
        "--hidden-import", "nastool_adapters",
        "--hidden-import", "websockets",  # 用于WebSocket监控
        "--exclude-module", "nastool_fixes.security",
        "nastool-cli/nastool_cli/main.py"
    ]
    
    subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)

# 打包启动器
def build_launcher():
    """打包启动器"""
    print("打包启动器...")
    # 创建启动器脚本
    launcher_script = PROJECT_ROOT / "launcher.py"
    launcher_content = '''
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NASTool 启动器
"""

import subprocess
import sys

if __name__ == "__main__":
    # 运行主程序
    subprocess.run(["nastool.exe"] + sys.argv[1:])
'''
    
    with open(launcher_script, "w", encoding="utf-8") as f:
        f.write(launcher_content)
    
    # PyInstaller命令
    cmd = [
        "pyinstaller",
        "--name", "nastool-launcher",
        "--onefile",
        "--console",
        "--clean",
        "launcher.py"
    ]
    
    subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)
    
    # 删除临时启动器脚本
    launcher_script.unlink()

# 复制配置文件和代理脚本
def copy_additional_files():
    """复制额外文件"""
    print("复制额外文件...")
    # 复制代理脚本
    agent_src = PROJECT_ROOT / "nastool-agent" / "nastool_agent.py"
    agent_dst = OUTPUT_DIR / "nastool_agent.py"
    if agent_src.exists():
        shutil.copy(agent_src, agent_dst)
        print(f"复制代理脚本: {agent_src} -> {agent_dst}")
    
    # 复制部署脚本
    deploy_src = PROJECT_ROOT / "deploy" / "deploy-nastool-agent.sh"
    deploy_dst = OUTPUT_DIR / "deploy-nastool-agent.sh"
    if deploy_src.exists():
        shutil.copy(deploy_src, deploy_dst)
        print(f"复制部署脚本: {deploy_src} -> {deploy_dst}")

# 测试打包结果
def test_build():
    """测试打包结果"""
    print("测试打包结果...")
    # 测试主可执行文件
    nastool_exe = OUTPUT_DIR / "nastool.exe"
    if nastool_exe.exists():
        print(f"主可执行文件: {nastool_exe}")
        # 测试版本信息
        result = subprocess.run(
            [str(nastool_exe), "--version"],
            capture_output=True,
            text=True
        )
        print(f"版本信息: {result.stdout.strip()}")
        if result.returncode != 0:
            print(f"版本测试失败: {result.stderr}")
        
        # 测试Mock模式
        result = subprocess.run(
            [str(nastool_exe), "--mock", "healthy"],
            capture_output=True,
            text=True
        )
        if "Health Score" in result.stdout:
            print("Mock模式测试成功")
        else:
            print(f"Mock模式测试失败: {result.stderr}")
    else:
        print("主可执行文件不存在")
    
    # 测试启动器
    launcher_exe = OUTPUT_DIR / "nastool-launcher.exe"
    if launcher_exe.exists():
        print(f"启动器: {launcher_exe}")
        # 测试启动器
        result = subprocess.run(
            [str(launcher_exe), "--version"],
            capture_output=True,
            text=True
        )
        print(f"启动器版本测试: {'成功' if result.returncode == 0 else '失败'}")
    else:
        print("启动器不存在")

# 主函数
def main():
    """主函数"""
    print("=" * 60)
    print("NASTool V4.1 打包脚本")
    print("=" * 60)
    
    try:
        # 清理输出目录
        clean_output()
        
        # 安装依赖
        install_dependencies()
        
        # 打包主可执行文件
        build_main_executable()
        
        # 打包启动器
        build_launcher()
        
        # 复制额外文件
        copy_additional_files()
        
        # 测试打包结果
        test_build()
        
        print("=" * 60)
        print("打包完成!")
        print(f"输出目录: {OUTPUT_DIR}")
        print("=" * 60)
        
    except Exception as e:
        print(f"打包失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())