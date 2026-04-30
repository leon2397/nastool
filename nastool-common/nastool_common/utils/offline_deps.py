import os
import sys
import platform
import subprocess
import shutil
from pathlib import Path

class OfflineDependencyManager:
    """
    离线依赖包管理器
    支持跨平台依赖管理，针对ARM/Linux环境优化
    """
    
    def __init__(self, deps_dir=None):
        self.deps_dir = deps_dir or os.path.join(os.path.dirname(__file__), '..', '..', 'dep')
        self.deps_dir = os.path.abspath(self.deps_dir)
        os.makedirs(self.deps_dir, exist_ok=True)
        
        # 依赖包目录结构
        self.wheels_dir = os.path.join(self.deps_dir, 'wheels')
        self.site_packages = os.path.join(self.deps_dir, 'site-packages')
        os.makedirs(self.wheels_dir, exist_ok=True)
        os.makedirs(self.site_packages, exist_ok=True)
    
    def detect_platform(self):
        """检测目标平台信息"""
        info = {
            'os': platform.system(),
            'arch': platform.machine(),
            'python_version': f"{sys.version_info.major}.{sys.version_info.minor}",
            'platform': platform.platform(),
            'linux_dist': platform.uname().release if platform.system() == 'Linux' else None
        }
        return info
    
    def get_platform_tag(self):
        """获取平台标签用于选择对应的依赖包"""
        system = platform.system().lower()
        arch = platform.machine().lower()
        
        # 标准化架构名称
        arch_map = {
            'x86_64': 'x86_64',
            'amd64': 'x86_64',
            'aarch64': 'aarch64',
            'arm64': 'aarch64',
            'armv7l': 'armv7l',
            'armhf': 'armv7l'
        }
        
        return f"{system}_{arch_map.get(arch, arch)}"
    
    def list_available_wheels(self):
        """列出可用的离线依赖包"""
        wheels = []
        if os.path.exists(self.wheels_dir):
            for f in os.listdir(self.wheels_dir):
                if f.endswith('.whl'):
                    wheels.append(f)
        return wheels
    
    def install_deps_from_offline(self, requirements_file=None):
        """从离线依赖包安装依赖"""
        platform_tag = self.get_platform_tag()
        installed = []
        skipped = []
        
        print(f"📦 检测到平台: {platform_tag}")
        print(f"📂 依赖目录: {self.deps_dir}")
        
        # 设置PYTHONPATH
        if self.site_packages not in sys.path:
            sys.path.insert(0, self.site_packages)
        
        # 安装wheel包
        wheels = self.list_available_wheels()
        for wheel in wheels:
            # 检查是否匹配当前平台
            if self._is_wheel_compatible(wheel, platform_tag):
                try:
                    self._install_wheel(wheel)
                    installed.append(wheel)
                except Exception as e:
                    print(f"⚠️ 安装失败 {wheel}: {e}")
                    skipped.append(wheel)
            else:
                skipped.append(wheel)
        
        print(f"\n✅ 已安装: {len(installed)} 个依赖")
        if skipped:
            print(f"⏭️ 跳过(不兼容): {len(skipped)} 个依赖")
        
        return installed, skipped
    
    def _is_wheel_compatible(self, wheel_name, platform_tag):
        """检查wheel包是否与当前平台兼容"""
        # 简化检查：查看平台标签是否匹配
        system_tag = platform_tag.split('_')[0]
        arch_tag = platform_tag.split('_')[1]
        
        # 纯Python包通常兼容所有平台
        if 'py3-none-any' in wheel_name:
            return True
        
        # 检查架构兼容性
        if arch_tag in wheel_name or 'any' in wheel_name:
            return True
        
        return False
    
    def _install_wheel(self, wheel_name):
        """安装单个wheel包"""
        wheel_path = os.path.join(self.wheels_dir, wheel_name)
        
        # 使用pip安装到指定目录
        cmd = [
            sys.executable, '-m', 'pip', 'install',
            '--no-deps',
            '--target', self.site_packages,
            wheel_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"pip安装失败: {result.stderr}")
        
        print(f"  ✓ {wheel_name}")
    
    def create_virtual_env(self, venv_dir=None):
        """创建虚拟环境"""
        venv_dir = venv_dir or os.path.join(self.deps_dir, 'venv')
        
        # 检查是否已存在
        if os.path.exists(venv_dir):
            print(f"⚠️ 虚拟环境已存在: {venv_dir}")
            return venv_dir
        
        # 创建虚拟环境
        cmd = [sys.executable, '-m', 'venv', venv_dir]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"创建虚拟环境失败: {result.stderr}")
        
        print(f"✅ 虚拟环境创建成功: {venv_dir}")
        return venv_dir
    
    def get_activation_script(self):
        """获取虚拟环境激活脚本路径"""
        venv_dir = os.path.join(self.deps_dir, 'venv')
        if platform.system() == 'Windows':
            return os.path.join(venv_dir, 'Scripts', 'activate.bat')
        else:
            return os.path.join(venv_dir, 'bin', 'activate')
    
    def setup_env(self):
        """设置运行环境"""
        # 添加site-packages到路径
        if self.site_packages not in sys.path:
            sys.path.insert(0, self.site_packages)
        
        # 设置环境变量
        os.environ.setdefault('NASTOOL_DEPS_DIR', self.deps_dir)
        os.environ.setdefault('PYTHONPATH', self.site_packages)
        
        print(f"✅ 环境设置完成")
        return True
    
    def download_deps(self, requirements_file, target_dir=None):
        """下载依赖包到本地（用于构建离线包）"""
        target_dir = target_dir or self.wheels_dir
        
        cmd = [
            sys.executable, '-m', 'pip', 'download',
            '-r', requirements_file,
            '-d', target_dir,
            '--no-cache-dir'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"下载依赖失败: {result.stderr}")
        
        print(f"✅ 依赖下载完成，共 {len(os.listdir(target_dir))} 个包")
        return target_dir
    
    def check_dependencies(self, required_deps):
        """检查依赖是否已安装"""
        missing = []
        for dep in required_deps:
            try:
                self._import_module(dep)
            except ImportError:
                missing.append(dep)
        return missing
    
    def _import_module(self, module_name):
        """尝试导入模块"""
        # 处理包名到模块名的转换
        module_map = {
            'paramiko': 'paramiko',
            'pyusb': 'usb',
            'requests': 'requests',
            'websocket-client': 'websocket',
            'pydantic': 'pydantic',
            'rich': 'rich',
            'psutil': 'psutil',
            'typing-extensions': 'typing_extensions',
            'packaging': 'packaging'
        }
        
        actual_name = module_map.get(module_name, module_name.replace('-', '_'))
        __import__(actual_name)
