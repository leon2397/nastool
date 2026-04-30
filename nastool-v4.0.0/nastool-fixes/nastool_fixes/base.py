# -*- coding: utf-8 -*-
"""
fixes/base.py - Base classes for all fixes

包含回滚机制的基类定义。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
import json
import os
from datetime import datetime


class RollbackStatus(Enum):
    """回滚状态枚举"""
    NOT_NEEDED = "not_needed"
    SUCCESSFUL = "successful"
    FAILED = "failed"
    NOT_SUPPORTED = "not_supported"


@dataclass
class FixResult:
    """Result of a fix execution"""

    fix_id: str
    success: bool
    message: str
    changed_files: List[str] = field(default_factory=list)
    commands_run: List[str] = field(default_factory=list)
    rollback_command: Optional[str] = None
    error: Optional[str] = None
    output: Optional[str] = None
    rollback_status: RollbackStatus = RollbackStatus.NOT_NEEDED
    rollback_message: Optional[str] = None


@dataclass
class RollbackInfo:
    """回滚信息"""
    fix_id: str
    timestamp: str
    original_state: Dict[str, Any]
    backup_files: List[str] = field(default_factory=list)
    rollback_commands: List[str] = field(default_factory=list)
    status: RollbackStatus = RollbackStatus.NOT_NEEDED
    message: Optional[str] = None


class Fix(ABC):
    """
    Abstract base class for all fixes

    所有修复模块的抽象基类，包含回滚机制支持。
    """

    fix_id: str = "base_fix"
    title: str = "Base Fix"
    description: str = "Base fix class"
    risk: str = "low"
    requires_root: bool = False
    supports_rollback: bool = False

    def __init__(self):
        """初始化修复模块"""
        self._rollback_info: Optional[RollbackInfo] = None
        self._backup_dir = os.path.expanduser("~/.nastool/fix_backups")

    @abstractmethod
    def is_applicable(self) -> bool:
        """
        Check if this fix is applicable.

        Returns:
            True if the fix can be applied
        """
        pass

    @abstractmethod
    def run(self) -> FixResult:
        """
        Execute the fix.

        Returns:
            FixResult with execution details
        """
        pass

    def rollback(self) -> FixResult:
        """
        回滚修复操作

        默认实现不支持回滚，子类可以重写实现具体的回滚逻辑。

        Returns:
            FixResult with rollback execution details
        """
        if not self.supports_rollback:
            return FixResult(
                fix_id=self.fix_id,
                success=False,
                message=f"修复模块 {self.fix_id} 不支持回滚",
                rollback_status=RollbackStatus.NOT_SUPPORTED,
            )

        if self._rollback_info is None:
            return FixResult(
                fix_id=self.fix_id,
                success=False,
                message="没有可用的回滚信息",
                rollback_status=RollbackStatus.FAILED,
            )

        return self._execute_rollback()

    def _execute_rollback(self) -> FixResult:
        """
        执行具体的回滚操作

        子类应该重写此方法实现具体的回滚逻辑。

        Returns:
            FixResult with rollback details
        """
        return FixResult(
            fix_id=self.fix_id,
            success=False,
            message="子类应重写 _execute_rollback 方法实现具体的回滚逻辑",
            rollback_status=RollbackStatus.NOT_SUPPORTED,
        )

    def _save_rollback_info(self, info: RollbackInfo):
        """
        保存回滚信息到磁盘

        Args:
            info: RollbackInfo 对象
        """
        try:
            os.makedirs(self._backup_dir, exist_ok=True)
            backup_file = os.path.join(
                self._backup_dir,
                f"{self.fix_id}_{info.timestamp.replace(':', '-')}.json"
            )

            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'fix_id': info.fix_id,
                    'timestamp': info.timestamp,
                    'original_state': info.original_state,
                    'backup_files': info.backup_files,
                    'rollback_commands': info.rollback_commands,
                    'status': info.status.value,
                    'message': info.message,
                }, f, indent=2, ensure_ascii=False)

            self._rollback_info = info
        except Exception as e:
            print(f"[WARN] 保存回滚信息失败: {e}")

    def _load_rollback_info(self, fix_id: str, timestamp: Optional[str] = None) -> Optional[RollbackInfo]:
        """
        从磁盘加载回滚信息

        Args:
            fix_id: 修复模块 ID
            timestamp: 时间戳（可选，如果不指定则加载最新的）

        Returns:
            RollbackInfo 对象或 None
        """
        try:
            os.makedirs(self._backup_dir, exist_ok=True)

            if timestamp:
                backup_file = os.path.join(
                    self._backup_dir,
                    f"{fix_id}_{timestamp.replace(':', '-')}.json"
                )
                if os.path.exists(backup_file):
                    with open(backup_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        return RollbackInfo(
                            fix_id=data['fix_id'],
                            timestamp=data['timestamp'],
                            original_state=data['original_state'],
                            backup_files=data.get('backup_files', []),
                            rollback_commands=data.get('rollback_commands', []),
                            status=RollbackStatus(data.get('status', 'not_needed')),
                            message=data.get('message'),
                        )
            else:
                files = [f for f in os.listdir(self._backup_dir)
                        if f.startswith(f"{fix_id}_") and f.endswith('.json')]
                if files:
                    files.sort(reverse=True)
                    return self._load_rollback_info(fix_id, files[0].replace(f"{fix_id}_", '').replace('.json', '').replace('-', ':'))

        except Exception as e:
            print(f"[WARN] 加载回滚信息失败: {e}")

        return None

    def _create_backup(self, file_path: str) -> Optional[str]:
        """
        备份文件

        Args:
            file_path: 要备份的文件路径

        Returns:
            备份文件的路径，失败返回 None
        """
        try:
            if not os.path.exists(file_path):
                return None

            os.makedirs(self._backup_dir, exist_ok=True)
            backup_path = os.path.join(
                self._backup_dir,
                f"{self.fix_id}_{os.path.basename(file_path)}.bak"
            )

            import shutil
            shutil.copy2(file_path, backup_path)
            return backup_path
        except Exception as e:
            print(f"[WARN] 备份文件 {file_path} 失败: {e}")
            return None

    def _restore_backup(self, backup_path: str, original_path: str) -> bool:
        """
        从备份恢复文件

        Args:
            backup_path: 备份文件路径
            original_path: 原始文件路径

        Returns:
            是否成功
        """
        try:
            if not os.path.exists(backup_path):
                return False

            import shutil
            shutil.copy2(backup_path, original_path)
            return True
        except Exception as e:
            print(f"[WARN] 恢复文件 {original_path} 失败: {e}")
            return False

    def _capture_state(self, file_path: str) -> Optional[str]:
        """
        捕获文件或配置项的当前状态

        Args:
            file_path: 文件路径或配置项

        Returns:
            当前状态的 JSON 字符串，失败返回 None
        """
        try:
            if os.path.exists(file_path):
                if os.path.isfile(file_path):
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    return json.dumps({
                        'type': 'file',
                        'path': file_path,
                        'content': content,
                        'size': os.path.getsize(file_path),
                        'mtime': os.path.getmtime(file_path),
                    }, ensure_ascii=False)
                elif os.path.isdir(file_path):
                    return json.dumps({
                        'type': 'directory',
                        'path': file_path,
                        'exists': True,
                    }, ensure_ascii=False)
            else:
                return json.dumps({
                    'type': 'file',
                    'path': file_path,
                    'exists': False,
                }, ensure_ascii=False)
        except Exception as e:
            print(f"[WARN] 捕获状态失败: {e}")
            return None

    def _run_command(self, cmd: str, timeout: int = 60) -> tuple:
        """
        Run shell command.

        Returns:
            (success, output) tuple
        """
        import subprocess

        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=timeout
            )
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, str(e)

    def _check_root(self) -> bool:
        """Check if running as root (cross-platform: Unix + Windows)"""
        import os
        import sys

        try:
            return os.geteuid() == 0
        except AttributeError:
            try:
                import ctypes
                return ctypes.windll.shell32.IsUserAnAdmin() != 0
            except Exception:
                return False

    def _confirm(self, message: str) -> bool:
        """
        Ask user for confirmation.

        Args:
            message: Confirmation prompt

        Returns:
            True if user confirms
        """
        try:
            response = input(f"{message} [y/N]: ").strip().lower()
            return response in ["y", "yes"]
        except EOFError:
            return False


def create_rollback_result(fix_id: str, success: bool, message: str,
                          status: RollbackStatus = RollbackStatus.NOT_NEEDED) -> FixResult:
    """
    创建回滚结果的便捷函数

    Args:
        fix_id: 修复模块 ID
        success: 是否成功
        message: 消息
        status: 回滚状态

    Returns:
        FixResult 对象
    """
    return FixResult(
        fix_id=fix_id,
        success=success,
        message=message,
        rollback_status=status,
    )
