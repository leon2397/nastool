"""
nastool Exceptions

Unified exception classes for consistent error handling with friendly hints.
"""

from typing import Optional, Any, Dict, List


class NastoolError(Exception):
    """Base exception for all nastool errors.

    All nastool-specific exceptions inherit from this class,
    making it easy to catch all nastool errors with a single except clause.

    Attributes:
        hint: Friendly hint for users on how to resolve the error

    Example:
        try:
            result = run_diagnostics()
        except NastoolError as e:
            print(f"Error: {e}")
            if e.hint:
                print(f"Hint: {e.hint}")
    """

    def __init__(self, message: str, hint: Optional[str] = None):
        self.hint = hint
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for API responses."""
        return {
            "error": self.__class__.__name__,
            "message": str(self),
            "hint": self.hint,
        }


class CheckFailedError(NastoolError):
    """Diagnostic check failed.

    Raised when a diagnostic check does not pass.

    Attributes:
        check_id: Identifier of the failed check
        message: Human-readable error message
        details: Optional additional details
        hint: Friendly hint for resolution
    """

    def __init__(
        self,
        check_id: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        hint: Optional[str] = None,
    ):
        self.check_id = check_id
        self.message = message
        self.details = details or {}

        # Auto-generate hint if not provided
        if not hint:
            hint = self._generate_hint(check_id, message, details)

        super().__init__(f"[{check_id}] {message}", hint=hint)

    def _generate_hint(self, check_id: str, message: str, details: Optional[Dict[str, Any]]) -> str:
        """Generate friendly hint based on check type"""
        hints = {
            "disk_space": "请检查磁盘空间，清理不必要的文件或扩展存储容量",
            "memory": "请关闭不必要的进程或增加内存",
            "temperature": "请检查散热系统，确保通风良好",
            "network": "请检查网络连接和DNS配置",
            "python_version": "请升级Python到3.8或更高版本",
            "pip_installed": "请安装pip: python -m ensurepip",
            "cuda_available": "请安装NVIDIA CUDA工具包和驱动",
        }
        return hints.get(check_id, f"请检查 {check_id} 相关配置")

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for API responses."""
        return {
            "error": "check_failed",
            "check_id": self.check_id,
            "message": self.message,
            "details": self.details,
            "hint": self.hint,
        }


class FixFailedError(NastoolError):
    """Auto-fix failed to apply.

    Attributes:
        fix_id: Identifier of the failed fix
        reason: Reason why the fix failed
        suggestion: Suggestion for manual resolution
    """

    def __init__(self, fix_id: str, reason: str, suggestion: Optional[str] = None):
        self.fix_id = fix_id
        self.reason = reason
        self.suggestion = suggestion

        msg = f"修复 '{fix_id}' 失败: {reason}"
        hint = suggestion or "请手动执行修复或联系系统管理员"

        super().__init__(msg, hint=hint)

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for API responses."""
        return {
            "error": "fix_failed",
            "fix_id": self.fix_id,
            "reason": self.reason,
            "suggestion": self.suggestion,
            "hint": self.hint,
        }


class DeviceNotDetectedError(NastoolError):
    """Could not detect device type.

    Attributes:
        hints: Optional hints about detected hardware
    """

    def __init__(self, hints: Optional[Dict[str, str]] = None):
        self.hints = hints or {}

        msg = "无法检测设备类型"
        hint = "请使用 --profile 参数指定设备类型，例如: --profile pi5"
        if hints:
            hint += f"\n检测到的硬件: {', '.join(f'{k}={v}' for k, v in hints.items())}"

        super().__init__(msg, hint=hint)

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for API responses."""
        return {
            "error": "device_not_detected",
            "hints": self.hints,
            "hint": self.hint,
        }


class ProfileNotFoundError(NastoolError):
    """Device profile not found.

    Attributes:
        profile_id: Requested profile identifier
        available: List of available profile IDs
    """

    def __init__(self, profile_id: str, available: Optional[List[str]] = None):
        self.profile_id = profile_id
        self.available = available or []

        msg = f"设备配置 '{profile_id}' 不存在"
        hint = "请使用 --list-profiles 查看可用的设备配置"
        if available:
            hint = f"可用的设备配置: {', '.join(available[:5])}"
            if len(available) > 5:
                hint += f" (还有 {len(available) - 5} 个)"

        super().__init__(msg, hint=hint)

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for API responses."""
        return {
            "error": "profile_not_found",
            "profile_id": self.profile_id,
            "available": self.available,
            "hint": self.hint,
        }


class ConfigurationError(NastoolError):
    """Configuration error.

    Attributes:
        config_key: Configuration key that has an issue
        expected: Expected value type or format
        actual: Actual value found
    """

    def __init__(self, config_key: str, expected: str, actual: Any):
        self.config_key = config_key
        self.expected = expected
        self.actual = actual

        msg = f"配置错误 '{config_key}': 期望 {expected}, 实际 '{actual}'"
        hint = f"请检查配置文件或环境变量 {config_key.upper()}"

        super().__init__(msg, hint=hint)

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for API responses."""
        return {
            "error": "configuration_error",
            "config_key": self.config_key,
            "expected": self.expected,
            "actual": str(self.actual),
            "hint": self.hint,
        }


class NetworkError(NastoolError):
    """Network connectivity error.

    Attributes:
        operation: Operation that failed
        target: Target host or URL
        original_error: Original exception if any
    """

    def __init__(self, operation: str, target: str, original_error: Optional[Exception] = None):
        self.operation = operation
        self.target = target
        self.original_error = original_error

        msg = f"网络错误: 无法 {operation} 到 {target}"
        hint = self._generate_hint(operation, target)

        super().__init__(msg, hint=hint)

    def _generate_hint(self, operation: str, target: str) -> str:
        """Generate friendly hint for network errors"""
        hints = [
            f"请检查目标服务是否启动: systemctl status ai-nas",
            f"请检查网络是否通畅: ping {target.split(':')[0] if ':' in target else target}",
            f"请检查端口是否开放: telnet {target}",
        ]
        return "\n".join(hints)

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for API responses."""
        return {
            "error": "network_error",
            "operation": self.operation,
            "target": self.target,
            "original_error": str(self.original_error) if self.original_error else None,
            "hint": self.hint,
        }


class PermissionError(NastoolError):
    """Permission denied error.

    Attributes:
        operation: Operation that requires permission
        required: Required permission level
    """

    def __init__(self, operation: str, required: str = "root"):
        self.operation = operation
        self.required = required

        msg = f"权限不足: {operation} 需要 {required} 权限"
        hint = f"请使用 sudo 运行此命令，或切换到 {required} 用户"

        super().__init__(msg, hint=hint)

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for API responses."""
        return {
            "error": "permission_denied",
            "operation": self.operation,
            "required": self.required,
            "hint": self.hint,
        }


class DependencyError(NastoolError):
    """Missing dependency error.

    Attributes:
        dependency: Name of the missing dependency
        install_hint: Hint for how to install
    """

    def __init__(self, dependency: str, install_hint: Optional[str] = None):
        self.dependency = dependency
        self.install_hint = install_hint

        msg = f"缺少依赖: {dependency}"
        hint = install_hint or f"请安装 {dependency}: pip install {dependency}"

        super().__init__(msg, hint=hint)

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for API responses."""
        return {
            "error": "dependency_missing",
            "dependency": self.dependency,
            "install_hint": self.install_hint,
            "hint": self.hint,
        }


class StorageError(NastoolError):
    """Storage related error.

    Attributes:
        path: Path that caused the error
        operation: Operation that failed
    """

    def __init__(self, path: str, operation: str, original_error: Optional[Exception] = None):
        self.path = path
        self.operation = operation
        self.original_error = original_error

        msg = f"存储错误: 无法 {operation} '{path}'"
        hint = self._generate_hint(path, operation)

        super().__init__(msg, hint=hint)

    def _generate_hint(self, path: str, operation: str) -> str:
        """Generate friendly hint for storage errors"""
        hints = {
            "read": f"请检查路径是否存在: ls -la {path}",
            "write": f"请检查写入权限: ls -la {path}\n请检查磁盘空间: df -h",
            "create": f"请检查父目录权限: ls -la {path}",
        }
        return hints.get(operation, f"请检查路径权限和磁盘空间: {path}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for API responses."""
        return {
            "error": "storage_error",
            "path": self.path,
            "operation": self.operation,
            "original_error": str(self.original_error) if self.original_error else None,
            "hint": self.hint,
        }


# Export all exceptions
__all__ = [
    "NastoolError",
    "CheckFailedError",
    "FixFailedError",
    "DeviceNotDetectedError",
    "ProfileNotFoundError",
    "ConfigurationError",
    "NetworkError",
    "PermissionError",
    "DependencyError",
    "StorageError",
]
