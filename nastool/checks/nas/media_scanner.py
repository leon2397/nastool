# -*- coding: utf-8 -*-
"""媒体索引服务检测"""
from __future__ import annotations
import subprocess
from checks.decorators import check

@check(id="media_indexer", category="NAS", title="Media Indexer",
       description="检测媒体库索引服务状态")
def media_scanner(ctx):
    procs = ["thumbnails", "fileindexer", "jellyfin", "plex", "emby", "sonarr", "radarr"]
    found = []
    for p in procs:
        try:
            r = subprocess.run(["pgrep", "-if", p], capture_output=True, timeout=5)
            if r.returncode == 0:
                found.append(p)
        except Exception:
            pass
    if found:
        return ctx.passed(current="running", expected="running",
                        message=f"Media indexer: {', '.join(found)}")
    return ctx.passed(current="not running", expected="running",
                    message="No media indexer detected", severity="INFO")
