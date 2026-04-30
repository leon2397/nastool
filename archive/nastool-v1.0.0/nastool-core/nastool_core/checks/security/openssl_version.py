# -*- coding: utf-8 -*-
"""OpenSSL 版本检测"""
from __future__ import annotations

import re
import subprocess
from nastool_core.checks.decorators import check

BAD_PREFIXES = ["1.0.0", "1.0.1", "1.0.2"]


@check(id="openssl_version", category="SECURITY", title="OpenSSL Version",
       description="检测 OpenSSL 版本，识别已知漏洞")
def openssl_version(ctx):
    try:
        r = subprocess.run(["openssl", "version"],
                          capture_output=True, text=True, timeout=5)
        if r.returncode != 0:
            return ctx.passed(current="unavailable",
                            expected="1.1.1+",
                            message="OpenSSL command not available",
                            severity="INFO")
        m = re.search(r"OpenSSL\s+(\d+\.\d+\.\d+[a-z]?)", r.stdout)
        version = m.group(1) if m else "unknown"
        for bad in BAD_PREFIXES:
            if version.startswith(bad):
                return ctx.failed(current=version,
                                expected="1.1.1+",
                                message=f"OpenSSL {version} has known vulnerabilities",
                                severity="CRITICAL",
                                fix_available=True, fix_id="update_openssl",
                                fix_command="apt update && apt upgrade openssl",
                                fix_description="Update OpenSSL to latest",
                                fix_risk="high")
        return ctx.passed(current=version,
                        expected="1.1.1+",
                        message=f"OpenSSL {version}")
    except Exception as e:
        return ctx.passed(current="unknown",
                        expected="1.1.1+",
                        message=f"Could not check OpenSSL: {e}",
                        severity="INFO")
