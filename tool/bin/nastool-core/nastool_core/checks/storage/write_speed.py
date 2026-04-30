# -*- coding: utf-8 -*-
"""Disk write speed check"""
from __future__ import annotations

import os
import tempfile
import time
from nastool_core.checks.decorators import check


@check(id="write_speed", category="STORAGE", title="Disk Write Speed",
       description="检查磁盘写入速度是否满足 NAS 需求")
def write_speed(ctx):
    try:
        test_data = os.urandom(1024 * 1024)  # 1MB
        with tempfile.NamedTemporaryFile(delete=False) as f:
            path = f.name
            start = time.time()
            for _ in range(100):
                f.write(test_data)
            f.flush()
            os.fsync(f.fileno())
            elapsed = time.time() - start
        os.unlink(path)
        mbps = (100 * 1024 * 1024 / elapsed) / (1024 * 1024)
        if mbps < 10:
            return ctx.failed(current=f"{mbps:.1f} MB/s",
                            expected=">=50 MB/s",
                            message=f"Too slow: {mbps:.1f} MB/s (< 10 MB/s)",
                            severity="CRITICAL",
                            fix_available=True, fix_id="check_disk",
                            fix_description="Use SSD or check disk health",
                            fix_risk="high")
        if mbps < 50:
            return ctx.passed(current=f"{mbps:.1f} MB/s",
                            expected=">=50 MB/s",
                            message=f"Slow: {mbps:.1f} MB/s",
                            severity="WARNING",
                            fix_available=True, fix_id="upgrade_disk",
                            fix_description="Consider SSD for better performance",
                            fix_risk="medium")
        return ctx.passed(current=f"{mbps:.1f} MB/s",
                        expected=">=50 MB/s",
                        message=f"{mbps:.1f} MB/s write speed OK")
    except Exception as e:
        return ctx.failed(current="error",
                        expected=">=50 MB/s",
                        message=f"Write test failed: {e}",
                        severity="CRITICAL")
