"""
core/safety.py - 安全底线 + 异常处理规范

V4.0 稳定性升级核心模块。

异常处理规范:
1. 禁止裸 except:
2. 禁止 except Exception: pass (吞掉异常)
3. 必须捕获具体异常类型
4. 所有异常必须记录日志
5. 可恢复异常返回默认值/False，不可恢复异常向上抛出

异常分类:
- 可恢复（检测失败，返回默认值）: subprocess.TimeoutExpired, FileNotFoundError, PermissionError
- 需要日志（操作失败）: paramiko.SSHException, requests.RequestException
- 致命错误（向上抛出）: MemoryError, SystemExit
"""

import logging
import subprocess
import functools
from typing import Any, Callable, List, Optional, ParamSpec, TypeVar
from pathlib import Path

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


# 常用异常类型分组
SSH_EXCEPTIONS = (
    # paramiko 异常（如果已安装）
    Exception,  # fallback，实际使用时应 import paramiko
)

SUBPROCESS_EXCEPTIONS = (
    subprocess.TimeoutExpired,
    subprocess.CalledProcessError,
    FileNotFoundError,
    PermissionError,
    OSError,
)

NETWORK_EXCEPTIONS = (
    # requests 异常（如果已安装）
    Exception,  # fallback
)

FILE_EXCEPTIONS = (
    FileNotFoundError,
    PermissionError,
    IsADirectoryError,
    UnicodeDecodeError,
)


def safe_subprocess(
    default: Any = None, timeout: int = 30, log_errors: bool = True
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    装饰器：安全执行 subprocess 命令

    用法:
        @safe_subprocess(default="", timeout=30)
        def get_hostname():
            return subprocess.check_output("hostname", shell=True, text=True)
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except subprocess.TimeoutExpired:
                if log_errors:
                    logger.warning(f"[{func.__name__}] 命令超时 ({timeout}s)")
                return default
            except subprocess.CalledProcessError as e:
                if log_errors:
                    logger.warning(f"[{func.__name__}] 命令失败: {e}")
                return default
            except FileNotFoundError:
                if log_errors:
                    logger.warning(f"[{func.__name__}] 命令未找到")
                return default
            except PermissionError:
                if log_errors:
                    logger.warning(f"[{func.__name__}] 权限不足")
                return default
            except OSError as e:
                if log_errors:
                    logger.warning(f"[{func.__name__}] 系统错误: {e}")
                return default

        return wrapper

    return decorator


def safe_file_op(
    default: Any = None, log_errors: bool = True
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    装饰器：安全执行文件操作

    用法:
        @safe_file_op(default={})
        def load_config(path: str) -> dict:
            return json.load(open(path))
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except FileNotFoundError:
                if log_errors:
                    logger.warning(f"[{func.__name__}] 文件未找到")
                return default
            except PermissionError:
                if log_errors:
                    logger.warning(f"[{func.__name__}] 权限不足")
                return default
            except UnicodeDecodeError:
                if log_errors:
                    logger.warning(f"[{func.__name__}] 编码错误")
                return default
            except json.JSONDecodeError as e:
                if log_errors:
                    logger.warning(f"[{func.__name__}] JSON 解析错误: {e}")
                return default

        return wrapper

    return decorator


class BackupManager:
    """
    备份管理器 - V4.0 安全底线核心

    所有破坏性操作前必须调用 backup() 创建备份。
    支持一键回滚。
    """

    MAX_BACKUPS = 5

    def __init__(self, backup_dir: Optional[Path] = None):
        self.backup_dir = backup_dir or Path("/tmp/nastools_backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def backup(self, file_path: Path | str) -> Optional[Path]:
        """
        创建备份

        Args:
            file_path: 要备份的文件路径

        Returns:
            备份文件路径，失败返回 None
        """
        file_path = Path(file_path)
        if not file_path.exists():
            logger.warning(f"备份失败: 文件不存在 {file_path}")
            return None

        import time

        timestamp = int(time.time())
        backup_name = f"{file_path.name}.bak.{timestamp}"
        backup_path = self.backup_dir / backup_name

        try:
            import shutil

            shutil.copy2(file_path, backup_path)
            logger.info(f"备份创建: {backup_path}")

            # 清理旧备份
            self._cleanup_old_backups(file_path.name)

            return backup_path
        except Exception as e:
            logger.error(f"备份失败: {e}")
            return None

    def list_backups(self, original_name: str) -> List[Path]:
        """列出指定文件的所有备份"""
        pattern = f"{original_name}.bak.*"
        backups = sorted(
            self.backup_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True
        )
        return backups

    def restore(self, backup_path: Path | str, target_path: Path | str) -> bool:
        """
        恢复备份

        Args:
            backup_path: 备份文件路径
            target_path: 目标文件路径

        Returns:
            成功返回 True
        """
        backup_path = Path(backup_path)
        target_path = Path(target_path)

        if not backup_path.exists():
            logger.error(f"恢复失败: 备份不存在 {backup_path}")
            return False

        try:
            import shutil

            # 先备份当前文件
            if target_path.exists():
                self.backup(target_path)

            shutil.copy2(backup_path, target_path)
            logger.info(f"恢复成功: {backup_path} -> {target_path}")
            return True
        except Exception as e:
            logger.error(f"恢复失败: {e}")
            return False

    def _cleanup_old_backups(self, original_name: str) -> int:
        """清理超过 MAX_BACKUPS 的旧备份"""
        backups = self.list_backups(original_name)
        removed = 0

        for old_backup in backups[self.MAX_BACKUPS :]:
            try:
                old_backup.unlink()
                removed += 1
            except Exception as e:
                logger.warning(f"清理备份失败: {e}")

        if removed:
            logger.info(f"清理 {removed} 个旧备份")

        return removed


# 全局备份管理器实例
backup_manager = BackupManager()
