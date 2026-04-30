# -*- coding: utf-8 -*-
"""
fixes/storage/create_paths.py - Create missing NAS storage paths

支持回滚机制。
"""

import os
from datetime import datetime
from typing import List, Dict, Any
from ..base import Fix, FixResult, RollbackInfo, RollbackStatus
from ..registry import register_fix


@register_fix
class CreatePathsFix(Fix):
    """Create missing NAS storage directories"""

    fix_id = "create_paths"
    title = "Create Storage Paths"
    description = "Create missing NAS storage directories"
    risk = "low"
    requires_root = False
    supports_rollback = True

    def is_applicable(self) -> bool:
        """Check if paths need to be created"""
        return True

    def run(self, paths=None) -> FixResult:
        """Create missing paths"""
        from checks.storage.path_exists import PathExistsCheck

        if paths is None:
            paths = PathExistsCheck.DEFAULT_PATHS

        commands_run = []
        created = []
        failed = []
        rollback_commands = []

        for path in paths:
            if not os.path.exists(path):
                try:
                    os.makedirs(path, exist_ok=True)
                    commands_run.append(f"mkdir -p {path}")
                    created.append(path)
                    rollback_commands.append(f"rmdir {path}")
                except Exception as e:
                    failed.append(f"{path}: {str(e)}")

        if failed:
            rollback_info = RollbackInfo(
                fix_id=self.fix_id,
                timestamp=datetime.now().isoformat(),
                original_state={'created_paths': [], 'existing_paths': list(paths)},
                backup_files=[],
                rollback_commands=[],
                status=RollbackStatus.NOT_NEEDED,
            )
            self._save_rollback_info(rollback_info)

            return FixResult(
                fix_id=self.fix_id,
                success=False,
                message=f"Created {len(created)} paths, failed {len(failed)}: {', '.join(failed[:3])}",
                commands_run=commands_run,
            )

        if created:
            rollback_info = RollbackInfo(
                fix_id=self.fix_id,
                timestamp=datetime.now().isoformat(),
                original_state={'created_paths': created, 'existing_paths': list(paths)},
                backup_files=[],
                rollback_commands=rollback_commands,
                status=RollbackStatus.NOT_NEEDED,
            )
            self._save_rollback_info(rollback_info)

            return FixResult(
                fix_id=self.fix_id,
                success=True,
                message=f"Created {len(created)} paths: {', '.join(created[:5])}",
                commands_run=commands_run,
            )

        rollback_info = RollbackInfo(
            fix_id=self.fix_id,
            timestamp=datetime.now().isoformat(),
            original_state={'created_paths': [], 'existing_paths': list(paths)},
            backup_files=[],
            rollback_commands=[],
            status=RollbackStatus.NOT_NEEDED,
        )
        self._save_rollback_info(rollback_info)

        return FixResult(
            fix_id=self.fix_id,
            success=True,
            message="All paths already exist",
            commands_run=commands_run,
        )

    def _execute_rollback(self) -> FixResult:
        """执行回滚操作"""
        rollback_info = self._rollback_info

        if rollback_info is None:
            rollback_info = self._load_rollback_info(self.fix_id)
            if rollback_info is None:
                return FixResult(
                    fix_id=self.fix_id,
                    success=False,
                    message="没有找到可用的回滚信息",
                    rollback_status=RollbackStatus.FAILED,
                )

        try:
            original_state = rollback_info.original_state
            created_paths = original_state.get('created_paths', [])

            if not created_paths:
                rollback_info.status = RollbackStatus.SUCCESSFUL
                rollback_info.message = "没有需要回滚的目录"

                return FixResult(
                    fix_id=self.fix_id,
                    success=True,
                    message="没有创建任何目录，无需回滚",
                    rollback_status=RollbackStatus.SUCCESSFUL,
                    rollback_message="无需回滚",
                )

            rollback_commands = []
            failed = []

            for path in created_paths:
                try:
                    if os.path.exists(path) and os.path.isdir(path):
                        os.rmdir(path)
                        rollback_commands.append(f"rmdir {path}")
                except Exception as e:
                    failed.append(f"{path}: {str(e)}")

            if failed:
                rollback_info.status = RollbackStatus.FAILED
                rollback_info.message = f"部分目录删除失败: {', '.join(failed[:3])}"

                return FixResult(
                    fix_id=self.fix_id,
                    success=False,
                    message=f"回滚部分成功，{len(rollback_commands)} 个目录已删除，{len(failed)} 个失败",
                    rollback_status=RollbackStatus.FAILED,
                    rollback_message=f"失败的目录: {', '.join(failed[:3])}",
                )

            rollback_info.status = RollbackStatus.SUCCESSFUL
            rollback_info.message = "所有创建的目录已删除"

            return FixResult(
                fix_id=self.fix_id,
                success=True,
                message=f"已删除 {len(created_paths)} 个目录",
                rollback_status=RollbackStatus.SUCCESSFUL,
                rollback_message="所有创建的目录已回滚删除",
            )

        except Exception as e:
            rollback_info.status = RollbackStatus.FAILED
            rollback_info.message = f"回滚异常: {str(e)}"

            return FixResult(
                fix_id=self.fix_id,
                success=False,
                message=f"回滚失败: {e}",
                rollback_status=RollbackStatus.FAILED,
            )

    def rollback(self) -> FixResult:
        """回滚修复操作"""
        print(f"[ROLLBACK] 正在回滚 {self.fix_id}...")

        result = super().rollback()

        if result.rollback_status == RollbackStatus.SUCCESSFUL:
            print(f"[OK] 回滚成功: {result.message}")
        elif result.rollback_status == RollbackStatus.NOT_SUPPORTED:
            print(f"[X] 此修复不支持回滚")
        elif result.rollback_status == RollbackStatus.FAILED:
            print(f"[X] 回滚失败: {result.message}")

        return result
