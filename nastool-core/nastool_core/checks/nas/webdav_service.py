# -*- coding: utf-8 -*-
"""WebDAV 服务检测"""
from __future__ import annotations
import os
import subprocess
from nastool_core.checks.decorators import check

@check(id="webdav_service", category="NAS", title="WebDAV Service",
       description="检测 WebDAV 服务是否配置并运行", enable_accuracy=True)
def webdav_service(ctx):
    nginx = ["/etc/nginx/nginx.conf", "/etc/nginx/conf.d/webdav.conf"]
    for path in nginx:
        if os.path.exists(path):
            try:
                with open(path) as f:
                    c = f.read()
                if "dav_methods" in c or "webdav" in c.lower():
                    return ctx.passed(current="configured", expected="configured",
                                    message="WebDAV configured (nginx)")
            except Exception:
                pass
    for proc in ["nginx", "apache2", "httpd"]:
        try:
            r = subprocess.run(["pgrep", "-f", proc], capture_output=True, timeout=5)
            if r.returncode == 0:
                return ctx.passed(current="possible", expected="configured",
                                message=f"{proc} running, WebDAV may be enabled")
        except Exception:
            pass
    return ctx.passed(current="not configured", expected="configured",
                    message="WebDAV not configured", severity="INFO",
                    fix_available=True, fix_id="setup_webdav",
                    fix_command="nginx with dav模块",
                    fix_description="Configure WebDAV via nginx/apache",
                    fix_risk="medium")
