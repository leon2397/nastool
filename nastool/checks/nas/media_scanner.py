# -*- coding: utf-8 -*-
"""媒体索引服务检测"""
import subprocess
from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check

@register_check
class MediaScannerCheck(Check):
    check_id = "media_indexer"
    title = "媒体索引"
    description = "检测媒体库索引服务状态（thumbnails/封面生成）"
    category = CheckCategory.NAS

    def run(self) -> CheckResult:
        procs = ["thumbnails", "fileindexer", "jellyfin", "plex", "emby", "sonarr", "radarr", "bazarr"]
        found = []
        for p in procs:
            try:
                result = subprocess.run(["pgrep", "-if", p], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    found.append(p)
            except Exception:
                pass

        if found:
            return CheckResult(
                check_id=self.check_id, title=self.title,
                category=self.category, passed=True,
                severity=CheckSeverity.PASSED,
                message=f"媒体索引服务: {', '.join(found)}",
                current="running", expected="running",
            )
        return CheckResult(
            check_id=self.check_id, title=self.title,
            category=self.category, passed=False,
            severity=CheckSeverity.INFO,
            message="未检测到媒体索引服务",
            current="not running", expected="running",
        )
