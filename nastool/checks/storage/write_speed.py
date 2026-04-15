"""
checks/storage/write_speed.py - Check disk write speed
"""

import os
import tempfile
import time
from ..base import Check, CheckResult, CheckSeverity, CheckCategory
from ..registry import register_check


@register_check
class WriteSpeedCheck(Check):
    """Check disk write speed meets NAS requirements"""

    check_id = "write_speed"
    title = "Disk Write Speed"
    description = "Check disk write speed for media storage"
    category = CheckCategory.STORAGE

    def run(self) -> CheckResult:
        """Run write speed benchmark"""
        # Write a 100MB test file
        test_size = 100 * 1024 * 1024  # 100MB
        test_data = os.urandom(1024 * 1024)  # 1MB random data

        try:
            with tempfile.NamedTemporaryFile(delete=False) as f:
                temp_path = f.name

                start = time.time()
                for _ in range(100):
                    f.write(test_data)
                f.flush()
                os.fsync(f.fileno())
                elapsed = time.time() - start

            # Calculate speed
            speed_mbps = (test_size / elapsed) / (1024 * 1024)

            # Cleanup
            os.unlink(temp_path)

            # Check thresholds
            if speed_mbps < 10:
                severity = CheckSeverity.CRITICAL
                passed = False
                message = f"Too slow: {speed_mbps:.1f} MB/s (< 10 MB/s)"
                fix = "Use SSD or check disk health"
            elif speed_mbps < 50:
                severity = CheckSeverity.WARNING
                passed = True
                message = f"Slow: {speed_mbps:.1f} MB/s (< 50 MB/s)"
                fix = "Consider SSD for better performance"
            else:
                severity = CheckSeverity.PASSED
                passed = True
                message = f"{speed_mbps:.1f} MB/s write speed"
                fix = None

            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=passed,
                severity=severity,
                message=message,
                current=f"{speed_mbps:.1f} MB/s",
                expected="≥50 MB/s",
                fix_available=fix is not None,
                fix_description=fix,
            )

        except Exception as e:
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=False,
                severity=CheckSeverity.CRITICAL,
                message=f"Write test failed: {str(e)}",
                current="Error",
                expected="≥50 MB/s",
            )
