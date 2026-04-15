"""
Friendly Error Messages for nastool

Converts technical errors into user-friendly messages with solutions.

Features:
- Error code mapping
- User-friendly messages in Chinese
- Concrete solutions
- Installation instructions

Usage:
    from utils.friendly_errors import FriendlyErrorHandler

    handler = FriendlyErrorHandler()
    message = handler.handle_error("ImportError: No module named 'yaml'")
    print(message)
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import re
from logger import get_logger

logger = get_logger(__name__)


class ErrorCategory(Enum):
    """Error category"""

    DEPENDENCY = "dependency"  # Missing dependency
    PERMISSION = "permission"  # Permission denied
    CONFIG = "config"  # Configuration error
    NETWORK = "network"  # Network error
    HARDWARE = "hardware"  # Hardware error
    SYSTEM = "system"  # System error
    UNKNOWN = "unknown"  # Unknown error


@dataclass
class FriendlyError:
    """User-friendly error representation"""

    code: str  # Error code
    category: ErrorCategory  # Error category
    title: str  # Short title
    message: str  # User-friendly message
    solution: str  # How to fix
    command: Optional[str] = None  # Command to fix (if any)
    docs_link: Optional[str] = None  # Link to documentation

    def format(self) -> str:
        """Format error for display"""
        lines = [
            "",
            f"❌ {self.title}",
            "",
            f"📋 问题：{self.message}",
            "",
            f"💡 解决方法：",
            f"   {self.solution}",
        ]

        if self.command:
            lines.append("")
            lines.append(f"🔧 执行命令：")
            lines.append(f"   {self.command}")

        if self.docs_link:
            lines.append("")
            lines.append(f"📚 文档：{self.docs_link}")

        lines.append("")

        return "\n".join(lines)


# Error mapping database
ERROR_MAP: Dict[str, FriendlyError] = {
    # Dependency errors
    "no_module_yaml": FriendlyError(
        code="E001",
        category=ErrorCategory.DEPENDENCY,
        title="缺少依赖：PyYAML",
        message="系统缺少 PyYAML 库，无法解析配置文件",
        solution="安装 PyYAML 库",
        command="pip install pyyaml",
    ),
    "no_module_requests": FriendlyError(
        code="E002",
        category=ErrorCategory.DEPENDENCY,
        title="缺少依赖：requests",
        message="系统缺少 requests 库，无法发送网络请求",
        solution="安装 requests 库",
        command="pip install requests",
    ),
    "no_module_psutil": FriendlyError(
        code="E003",
        category=ErrorCategory.DEPENDENCY,
        title="缺少依赖：psutil",
        message="系统缺少 psutil 库，无法获取系统信息",
        solution="安装 psutil 库",
        command="pip install psutil",
    ),
    "no_module_nvidia": FriendlyError(
        code="E004",
        category=ErrorCategory.DEPENDENDENCY,
        title="缺少依赖：pynvml",
        message="系统缺少 pynvml 库，无法检测 NVIDIA GPU",
        solution="安装 pynvml 库",
        command="pip install pynvml",
    ),
    # Permission errors
    "permission_denied": FriendlyError(
        code="E101",
        category=ErrorCategory.PERMISSION,
        title="权限不足",
        message="当前用户没有执行此操作的权限",
        solution="使用 sudo 或管理员权限运行",
        command="sudo python arm_diagnose.py",
    ),
    "file_permission_denied": FriendlyError(
        code="E102",
        category=ErrorCategory.PERMISSION,
        title="文件权限不足",
        message="无法读写配置文件或日志文件",
        solution="修改文件权限或使用 sudo 运行",
        command="chmod 644 config.yaml",
    ),
    # Config errors
    "config_not_found": FriendlyError(
        code="E201",
        category=ErrorCategory.CONFIG,
        title="配置文件不存在",
        message="找不到 config.yaml 配置文件",
        solution="运行配置向导创建配置文件",
        command="python arm_diagnose.py --setup",
    ),
    "config_invalid_yaml": FriendlyError(
        code="E202",
        category=ErrorCategory.CONFIG,
        title="配置文件格式错误",
        message="config.yaml 文件格式不正确，无法解析",
        solution="检查 YAML 语法或重新生成配置",
        command="python arm_diagnose.py --setup",
    ),
    "config_missing_field": FriendlyError(
        code="E203",
        category=ErrorCategory.CONFIG,
        title="配置项缺失",
        message="配置文件中缺少必要的配置项",
        solution="检查配置文件或重新生成",
        command="python arm_diagnose.py --setup",
    ),
    # Network errors
    "network_timeout": FriendlyError(
        code="E301",
        category=ErrorCategory.NETWORK,
        title="网络连接超时",
        message="无法连接到目标服务器，请检查网络连接",
        solution="检查网络设置或稍后重试",
        command="ping 8.8.8.8",
    ),
    "nas_unreachable": FriendlyError(
        code="E302",
        category=ErrorCategory.NETWORK,
        title="NAS 后端无法连接",
        message="无法连接到 NAS 后端服务器，请确认地址正确且服务运行中",
        solution="检查 NAS 服务状态和网络连接",
        command="curl http://localhost:8000/health",
    ),
    "dns_failed": FriendlyError(
        code="E303",
        category=ErrorCategory.NETWORK,
        title="DNS 解析失败",
        message="无法解析域名，请检查 DNS 设置",
        solution="修改 DNS 设置为 8.8.8.8 或 223.5.5.5",
        command="echo 'nameserver 8.8.8.8' | sudo tee /etc/resolv.conf",
    ),
    # Hardware errors
    "no_gpu_detected": FriendlyError(
        code="E401",
        category=ErrorCategory.HARDWARE,
        title="未检测到 GPU",
        message="系统未检测到 NVIDIA GPU，AI 功能将受限",
        solution="安装 NVIDIA 驱动或检查硬件连接",
        command="nvidia-smi || echo 'GPU 驱动未安装'",
    ),
    "cuda_not_available": FriendlyError(
        code="E402",
        category=ErrorCategory.HARDWARE,
        title="CUDA 不可用",
        message="CUDA Toolkit 未安装或版本不兼容",
        solution="安装 CUDA Toolkit 11.x 或 12.x",
        command="nvcc --version || echo 'CUDA 未安装'",
        docs_link="https://developer.nvidia.com/cuda-downloads",
    ),
    "disk_critical": FriendlyError(
        code="E403",
        category=ErrorCategory.HARDWARE,
        title="磁盘空间严重不足",
        message="磁盘剩余空间少于 10%，系统可能无法正常运行",
        solution="立即清理磁盘空间",
        command="python arm_diagnose.py --fix --auto",
    ),
    "memory_critical": FriendlyError(
        code="E404",
        category=ErrorCategory.HARDWARE,
        title="内存严重不足",
        message="内存使用率超过 95%，系统可能崩溃",
        solution="释放内存或增加 swap",
        command="free -h",
    ),
    # System errors
    "python_version": FriendlyError(
        code="E501",
        category=ErrorCategory.SYSTEM,
        title="Python 版本过低",
        message="需要 Python 3.8 或更高版本",
        solution="升级 Python 版本",
        command="python3 --version",
    ),
    "os_unsupported": FriendlyError(
        code="E502",
        category=ErrorCategory.SYSTEM,
        title="操作系统不支持",
        message="当前操作系统不在支持列表中",
        solution="使用支持的操作系统（Ubuntu/Debian/CentOS 等）",
        docs_link="https://github.com/your-repo/nastool#supported-systems",
    ),
}


class FriendlyErrorHandler:
    """
    Handler for converting technical errors to friendly messages.

    Usage:
        handler = FriendlyErrorHandler()

        # Handle exception
        friendly = handler.handle_exception(e)
        print(friendly.format())

        # Handle error string
        friendly = handler.handle_error("ImportError: No module named 'yaml'")
        print(friendly.format())
    """

    def __init__(self):
        self.pattern_handlers = [
            # Python import errors
            (r"No module named ['\"](\w+)['\"]", self._handle_missing_module),
            (r"ModuleNotFoundError: No module named ['\"](\w+)['\"]", self._handle_missing_module),
            (r"ImportError:.*['\"](\w+)['\"]", self._handle_missing_module),
            # Permission errors
            (r"Permission denied", self._handle_permission_denied),
            (r"PermissionError:.*'([^']+)'", self._handle_permission_denied),
            (r"Access is denied", self._handle_permission_denied),
            # Network errors
            (r"Connection timed out", self._handle_network_timeout),
            (r"Connection refused", self._handle_network_refused),
            (r"Name or service not known", self._handle_dns_failed),
            (r"getaddrinfo failed", self._handle_dns_failed),
            # Config errors
            (r"config\.yaml.*not found", self._handle_config_not_found),
            (r"YAML.*error", self._handle_config_invalid),
            (r"ParserError", self._handle_config_invalid),
        ]

    def handle_exception(self, exception: Exception) -> FriendlyError:
        """Handle Python exception"""
        error_str = str(exception)
        error_type = type(exception).__name__

        return self.handle_error(f"{error_type}: {error_str}")

    def handle_error(self, error_str: str) -> FriendlyError:
        """Handle error string"""
        # Try pattern matching
        for pattern, handler in self.pattern_handlers:
            match = re.search(pattern, error_str, re.IGNORECASE)
            if match:
                return handler(match, error_str)

        # Fallback to generic error
        return self._create_generic_error(error_str)

    def _handle_missing_module(self, match, error_str: str) -> FriendlyError:
        """Handle missing Python module"""
        module_name = match.group(1)

        # Map common module names
        module_map = {
            "yaml": "no_module_yaml",
            "requests": "no_module_requests",
            "psutil": "no_module_psutil",
            "pynvml": "no_module_nvidia",
            "nvml": "no_module_nvidia",
        }

        error_key = module_map.get(module_name.lower())

        if error_key and error_key in ERROR_MAP:
            return ERROR_MAP[error_key]

        # Generic module error
        return FriendlyError(
            code="E000",
            category=ErrorCategory.DEPENDENCY,
            title=f"缺少依赖：{module_name}",
            message=f"系统缺少 {module_name} 库",
            solution=f"安装 {module_name} 库",
            command=f"pip install {module_name}",
        )

    def _handle_permission_denied(self, match, error_str: str) -> FriendlyError:
        """Handle permission denied error"""
        if "file" in error_str.lower() or "." in error_str:
            return ERROR_MAP["file_permission_denied"]
        return ERROR_MAP["permission_denied"]

    def _handle_network_timeout(self, match, error_str: str) -> FriendlyError:
        """Handle network timeout"""
        return ERROR_MAP["network_timeout"]

    def _handle_network_refused(self, match, error_str: str) -> FriendlyError:
        """Handle connection refused"""
        if "8000" in error_str or "nas" in error_str.lower():
            return ERROR_MAP["nas_unreachable"]
        return ERROR_MAP["network_timeout"]

    def _handle_dns_failed(self, match, error_str: str) -> FriendlyError:
        """Handle DNS failure"""
        return ERROR_MAP["dns_failed"]

    def _handle_config_not_found(self, match, error_str: str) -> FriendlyError:
        """Handle config not found"""
        return ERROR_MAP["config_not_found"]

    def _handle_config_invalid(self, match, error_str: str) -> FriendlyError:
        """Handle invalid config"""
        return ERROR_MAP["config_invalid_yaml"]

    def _create_generic_error(self, error_str: str) -> FriendlyError:
        """Create generic error for unknown errors"""
        # Truncate long error messages
        short_msg = error_str[:100] + "..." if len(error_str) > 100 else error_str

        return FriendlyError(
            code="E999",
            category=ErrorCategory.UNKNOWN,
            title="未知错误",
            message=short_msg,
            solution="查看日志文件获取详细信息，或联系技术支持",
            docs_link="https://github.com/your-repo/nastool/issues",
        )


if __name__ == "__main__":
    # Demo
    handler = FriendlyErrorHandler()

    print("=" * 60)
    print("友好错误提示示例")
    print("=" * 60)

    # Test cases
    test_errors = [
        "ImportError: No module named 'yaml'",
        "PermissionError: [Errno 13] Permission denied: '/etc/config.yaml'",
        "Connection timed out",
        "FileNotFoundError: config.yaml not found",
        "Unknown weird error that doesn't match anything",
    ]

    for error in test_errors:
        print()
        print(f"原始错误: {error}")
        print("-" * 60)
        friendly = handler.handle_error(error)
        print(friendly.format())
