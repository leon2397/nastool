# -*- coding: utf-8 -*-
"""NAS 存储路径检测"""
from __future__ import annotations

import os
from nastool_core.checks.decorators import check

DEFAULT_PATHS = ["/nas", "/nas/media", "/nas/photos", "/nas/videos"]


@check(id="path_exists", category="STORAGE", title="Storage Paths",
       description="检查 NAS 存储路径是否存在")
def path_exists(ctx, paths=None):
    paths = paths or DEFAULT_PATHS
    missing, existing = [], []
    for p in paths:
        if os.path.exists(p):
            existing.append(p)
        else:
            missing.append(p)
    if not missing:
        return ctx.passed(current=f"{len(existing)}/{len(paths)} paths",
                        expected="All paths exist",
                        message=f"All {len(existing)} paths exist")
    msg = f"Missing {len(missing)}/{len(paths)}: {', '.join(missing[:3])}"
    sev = "CRITICAL" if not existing else "WARNING"
    return ctx.failed(current=f"{len(existing)}/{len(paths)} paths",
                    expected="All paths exist",
                    message=msg,
                    severity=sev,
                    fix_available=True, fix_id="create_paths",
                    fix_command=f"mkdir -p {' '.join(missing)}",
                    fix_description="Create missing directories",
                    fix_risk="low")
