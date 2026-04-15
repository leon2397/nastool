# -*- coding: utf-8 -*-
"""WebDAV 服务检测"""

import subprocess

from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check


@register_check
class WebDAVCheck(Check):
    """检测 WebDAV 服务状态"""

    check_id = "webdav_service"
    title = "WebDAV 服务"
    description = "检测 WebDAV 服务是否配置并运行"
    category = CheckCategory.NAS

    def run(self) -> CheckResult:
        # 检查 nginx/apache 对 WebDAV 的配置
        nginx_configs = ["/etc/nginx/nginx.conf", "/etc/nginx/conf.d/webdav.conf"]
        apache_configs = ["/etc/httpd/conf/httpd.conf", "/etc/apache2/sites-enabled/"]

        for path in nginx_configs:
            if self._file_exists(path):
                try:
                    with open(path) as f:
                        content = f.read()
                    if "dav_methods" in content or "webdav" in content.lower():
                        return CheckResult(
                            check_id=self.check_id, title=self.title,
                            category=self.category, passed=True,
                            severity=CheckSeverity.PASSED,
                            message="WebDAV 已配置（nginx）",
                            current="configured",
                            expected="running",
                        )
                except Exception:
                    pass

        # 检查进程
        for proc in ["nginx", "apache2", "httpd"]:
            try:
                result = subprocess.run(["pgrep", "-f", proc], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    return CheckResult(
                        check_id=self.check_id, title=self.title,
                        category=self.category, passed=True,
                        severity=CheckSeverity.PASSED,
                        message=f"Web 服务器运行中，WebDAV 可能已启用",
                        current="possible",
                        expected="configured",
                    )
            except Exception:
                pass

        return CheckResult(
            check_id=self.check_id, title=self.title,
            category=self.category, passed=False,
            severity=CheckSeverity.INFO,
            message="WebDAV 服务未配置",
            current="not configured",
            expected="configured",
            fix_available=True,
            fix_id="setup_webdav",
            fix_description="通过 nginx/apache 配置 WebDAV",
            fix_risk="medium",
        )
