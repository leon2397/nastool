# -*- coding: utf-8 -*-
"""
Example plugin: RK Performance Monitor

Demonstrates how to write a NASTool plugin.
This plugin adds:
- A custom RK device check (npu_thermal_budget)
- A custom RK adapter (rk_device)

Install this plugin by copying this file to:
  ~/.config/nastool/plugins/rk_perf_monitor.py
  OR: pip install this package (with entry_points configured)
"""

from nastool_core.plugin.base import NastoolPlugin, PluginMetadata


class RKPerfMonitorPlugin(NastoolPlugin):
    """
    Rockchip Performance Monitor Plugin.

    Monitors NPU thermal budget and frequency throttling on RK3588/RK3568.
    """

    name = "rk-perf-monitor"
    version = "1.0.0"
    description = "Rockchip NPU thermal & frequency monitoring plugin"
    author = "NASTool Community"
    tags = ["rockchip", "npu", "thermal", "performance"]

    def register_checks(self):
        """Register custom Rockchip performance checks."""
        from nastool_core.checks.base import Check, CheckResult, CheckSeverity, CheckCategory

        class NPUThermalBudgetCheck(Check):
            """
            Check NPU thermal budget.

            RK3588 thermal budget: 80C sustained, 85C throttle, 105C max.
            """
            check_id = "npu_thermal_budget"
            category = CheckCategory.AI
            title = "NPU Thermal Budget"
            description = "Check if NPU stays within thermal budget"

            def run(self) -> CheckResult:
                import os

                # Read NPU temperature
                npu_temp = None
                for path in [
                    "/sys/class/thermal/thermal_zone0/temp",
                    "/sys/class/rknpu/rknpu0/temp",
                ]:
                    if os.path.exists(path):
                        try:
                            with open(path) as f:
                                raw = int(f.read().strip())
                                npu_temp = raw / 1000.0
                            break
                        except Exception:
                            pass

                if npu_temp is None:
                    return CheckResult(
                        check_id=self.check_id,
                        category=self.category,
                        severity=CheckSeverity.WARNING,
                        passed=False,
                        title=self.title,
                        current="unknown",
                        expected="< 75C",
                        message="Could not read NPU temperature",
                    )

                # Evaluate
                if npu_temp < 70:
                    sev = CheckSeverity.PASSED
                    passed = True
                    msg = f"NPU temperature {npu_temp}C is healthy"
                elif npu_temp < 80:
                    sev = CheckSeverity.INFO
                    passed = True
                    msg = f"NPU temperature {npu_temp}C is warm but within budget"
                elif npu_temp < 85:
                    sev = CheckSeverity.WARNING
                    passed = False
                    msg = f"NPU temperature {npu_temp}C is approaching throttle threshold"
                else:
                    sev = CheckSeverity.CRITICAL
                    passed = False
                    msg = f"NPU temperature {npu_temp}C has throttled!"

                return CheckResult(
                    check_id=self.check_id,
                    category=self.category,
                    severity=sev,
                    passed=passed,
                    title=self.title,
                    current=f"{npu_temp}C",
                    expected="< 75C",
                    message=msg,
                    fix_available=(npu_temp >= 80),
                    fix_description="Improve NPU cooling: add heatsink or fan",
                )

        class RKFrequencyThrottleCheck(Check):
            """
            Check if NPU/GPU is being throttled due to thermal or power limits.
            """
            check_id = "rk_freq_throttle"
            category = CheckCategory.AI
            title = "Frequency Throttle Status"
            description = "Check if RK chip is throttling frequency"

            def run(self) -> CheckResult:
                import os

                throttled = False
                reason = "none"

                # Check various throttle indicators
                throttle_paths = {
                    "npu_throttle": "/sys/class/rknpu/rknpu0/throttle",
                    "gpu_throttle": "/sys/class/devfreq/fb000000.gpu/cur_freq",
                    "cpu_throttle": "/sys/devices/system/cpu/cpufreq/policy0/scaling_cur_freq",
                }

                for name, path in throttle_paths.items():
                    if os.path.exists(path):
                        try:
                            with open(path) as f:
                                val = f.read().strip()
                            # freq == 0 usually means throttled
                            if val == "0":
                                throttled = True
                                reason = name
                                break
                        except Exception:
                            pass

                # Check devfreq available frequencies
                devfreq_path = "/sys/class/devfreq"
                if os.path.exists(devfreq_path) and not throttled:
                    try:
                        for subdir in os.listdir(devfreq_path):
                            freq_file = os.path.join(devfreq_path, subdir, "cur_freq")
                            target_file = os.path.join(devfreq_path, subdir, "target_freq")
                            if os.path.exists(freq_file) and os.path.exists(target_file):
                                with open(freq_file) as f:
                                    cur = int(f.read().strip())
                                with open(target_file) as f:
                                    tgt = int(f.read().strip())
                                # If current < 80% of target, likely throttling
                                if tgt > 0 and cur < tgt * 0.8:
                                    throttled = True
                                    reason = f"{subdir}: cur={cur} < 80% of target={tgt}"
                                    break
                    except Exception:
                        pass

                if not throttled:
                    return CheckResult(
                        check_id=self.check_id,
                        category=self.category,
                        severity=CheckSeverity.PASSED,
                        passed=True,
                        title=self.title,
                        current="no throttle",
                        expected="no throttle",
                        message="All frequencies operating at target",
                    )
                else:
                    return CheckResult(
                        check_id=self.check_id,
                        category=self.category,
                        severity=CheckSeverity.WARNING,
                        passed=False,
                        title=self.title,
                        current=f"throttled ({reason})",
                        expected="no throttle",
                        message=f"Device throttling detected: {reason}",
                        fix_available=True,
                        fix_description="Check thermal paste, heatsink, and fan operation",
                    )

        return [NPUThermalBudgetCheck, RKFrequencyThrottleCheck]

    def register_adapters(self):
        """Register a custom Rockchip device adapter."""
        # Import here to avoid hard dependency on nastool_adapters
        from nastool_adapters.base import BaseAdapter, AdapterResult, ErrorCode

        class RKPerfDeviceAdapter(BaseAdapter):
            """
            Adapter for Rockchip devices with performance monitoring.
            """

            adapter_name = "rk-perf"

            def __init__(self, config=None):
                super().__init__(config)
                self._config = config or {}

            def health_check(self) -> AdapterResult:
                result = AdapterResult(
                    adapter_name=self.adapter_name,
                    device_name="Rockchip Perf Device",
                    device_type="rockchip",
                    backend_type="rk_perf",
                    backend_version="1.0.0",
                )

                # Run the thermal budget check
                from nastool_core.checks.base import CheckSeverity

                for check_cls in RKPerfMonitorPlugin().register_checks():
                    chk = check_cls()
                    res = chk.run()
                    result.add_check_result(res)

                return result

            def get_device_info(self):
                return {
                    "device_name": "Rockchip Performance Monitor",
                    "device_type": "rockchip",
                    "version": "1.0.0",
                }

        return [("rk-perf", RKPerfDeviceAdapter)]


# Auto-register when imported
def _register():
    from nastool_core.plugin import register_plugin
    register_plugin(RKPerfMonitorPlugin)


_register()
