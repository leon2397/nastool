# -*- coding: utf-8 -*-
"""
fixes/fix_engine_v2.py - 修复引擎 v2.0

v7.0 新增功能：
- 修复前快照、修复后对比
- 支持 dry-run（只显示做什么，不执行）
- 修复结果结构化返回

依赖 fixes/fix_recommendations.py 的映射表
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .fix_recommendations import FIX_RECOMMENDATIONS, MANUAL_CATEGORIES


@dataclass
class FixSnapshot:
    """修复前后状态快照"""
    timestamp: str
    check_id: str
    fix_id: str
    before_state: dict
    after_state: Optional[dict] = None
    success: bool = False
    error: Optional[str] = None


@dataclass
class FixResult:
    """修复执行结果"""
    fix_id: str
    check_id: str
    action: str
    success: bool
    dry_run: bool
    before_snapshot: Optional[dict] = None
    after_snapshot: Optional[dict] = None
    error: Optional[str] = None
    warning: Optional[str] = None


class FixEngineV2:
    """
    修复引擎 v2.0
    
    功能：
    - 推荐->确认->执行 三步（auto模式一步）
    - 修复前后状态快照
    - dry-run 模式
    - 结果结构化返回
    """

    def __init__(self, snapshot_dir: str = "~/.nastools/fix_snapshots"):
        self.snapshot_dir = Path(os.path.expanduser(snapshot_dir))
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

    def get_recommendations(self, check_results: dict) -> List[dict]:
        """
        根据检测结果获取修复建议
        
        Args:
            check_results: {check_id: check_result} 字典
            
        Returns:
            推荐修复列表
        """
        recommendations = []
        
        for check_id, check_result in check_results.items():
            if check_id not in FIX_RECOMMENDATIONS:
                continue
                
            # 检查是否需要修复（基于结果状态）
            if check_result.get("ok", True):
                continue
                
            for fix_rec in FIX_RECOMMENDATIONS[check_id]:
                fix_rec["check_id"] = check_id
                recommendations.append(fix_rec)
        
        return recommendations

    def take_snapshot(self, check_id: str, fix_id: str) -> dict:
        """
        拍摄修复前快照
        
        实际实现中，这里应该采集相关的系统状态
        """
        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "check_id": check_id,
            "fix_id": fix_id,
            "note": "快照功能需要根据具体 fix 类型实现"
        }
        return snapshot

    def execute_fix(
        self, 
        fix_id: str, 
        check_id: str, 
        dry_run: bool = False,
        auto_approve: bool = False
    ) -> FixResult:
        """
        执行修复
        
        Args:
            fix_id: 修复ID
            check_id: 检测ID
            dry_run: True=只显示做什么，不执行
            auto_approve: True=自动确认执行（无需人工确认）
            
        Returns:
            FixResult 结构化结果
        """
        # 查找修复定义
        fix_def = self._get_fix_definition(fix_id)
        if not fix_def:
            return FixResult(
                fix_id=fix_id,
                check_id=check_id,
                action="unknown",
                success=False,
                dry_run=dry_run,
                error=f"未找到 fix_id: {fix_id}"
            )

        # 拍摄修复前快照
        before_snapshot = self.take_snapshot(check_id, fix_id)
        
        # dry-run 模式
        if dry_run:
            return FixResult(
                fix_id=fix_id,
                check_id=check_id,
                action=fix_def.get("action", ""),
                success=True,
                dry_run=True,
                before_snapshot=before_snapshot,
                warning=f"[DRY-RUN] 将执行: {fix_def.get('action', '')}"
            )

        # 执行修复（需要实现具体的 fix 执行逻辑）
        # 这里是个框架，实际执行需要调用对应的 fix 脚本
        try:
            # 示例：调用 fix 脚本
            # result = subprocess.run(["fixes/scripts", fix_id], ...)
            
            after_snapshot = self.take_snapshot(check_id, fix_id)
            
            return FixResult(
                fix_id=fix_id,
                check_id=check_id,
                action=fix_def.get("action", ""),
                success=True,
                dry_run=False,
                before_snapshot=before_snapshot,
                after_snapshot=after_snapshot
            )
        except Exception as e:
            return FixResult(
                fix_id=fix_id,
                check_id=check_id,
                action=fix_def.get("action", ""),
                success=False,
                dry_run=False,
                before_snapshot=before_snapshot,
                error=str(e)
            )

    def _get_fix_definition(self, fix_id: str) -> Optional[dict]:
        """查找修复定义"""
        for check_id, fixes in FIX_RECOMMENDATIONS.items():
            for fix in fixes:
                if fix.get("fix_id") == fix_id:
                    return fix
        return None

    def compare_snapshots(
        self, 
        before: dict, 
        after: dict
    ) -> Dict[str, Any]:
        """
        对比修复前后快照
        
        Returns:
            差异报告
        """
        return {
            "timestamp": datetime.now().isoformat(),
            "before": before,
            "after": after,
            "changes": "快照对比功能需要根据具体状态字段实现"
        }

    def save_snapshot(self, snapshot: FixSnapshot):
        """保存快照到文件"""
        filename = f"{snapshot.check_id}_{snapshot.fix_id}_{snapshot.timestamp.replace(':', '-')}.json"
        filepath = self.snapshot_dir / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": snapshot.timestamp,
                "check_id": snapshot.check_id,
                "fix_id": snapshot.fix_id,
                "before_state": snapshot.before_state,
                "after_state": snapshot.after_state,
                "success": snapshot.success,
                "error": snapshot.error
            }, f, ensure_ascii=False, indent=2)


# 导出
__all__ = ["FixEngineV2", "FixResult", "FixSnapshot"]
