# -*- coding: utf-8 -*-
"""代理配置检测"""
from __future__ import annotations

import os
from checks.decorators import check


@check(id="proxy_config", category="NETWORK", title="Proxy Configuration",
       description="检测系统代理环境变量配置")
def proxy_check(ctx):
    for var in ["http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"]:
        val = os.environ.get(var, "")
        if val:
            return ctx.passed(current="configured",
                             expected="none or configured",
                             message=f"Proxy set: {var}={val[:60]}",
                             severity="INFO")
    return ctx.passed(current="none",
                     expected="none",
                     message="No proxy configured")
