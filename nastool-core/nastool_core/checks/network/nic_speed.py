from typing import Optional
"""
checks/network/nic_speed.py - NIC link speed check
检查网卡 link speed（1Gbps / 2.5Gbps / 10Gbps）
"""

import subprocess
import re
from ..base import Check, CheckResult, CheckSeverity, CheckCategory
from ..registry import register_check


@register_check
class NICSpeedCheck(Check):
    """Check network interface card link speeds"""

    check_id = "nic_speed"
    title = "网卡速率检测"
    description = "检测网卡 link speed，确保 NAS 网络性能达标"
    category = CheckCategory.NETWORK

    # 理想速率（Mbps）
    IDEAL_SPEED = 1000  # 1Gbps
    WARNING_SPEED = 100  # 100Mbps 以下警告
    SLOW_SPEED = 10      # 10Mbps 严重

    def run(self) -> CheckResult:
        """Run NIC speed check"""
        nics = self._get_nic_speeds()

        if not nics:
            return self._enhance_result_with_accuracy(CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=True,
                severity=CheckSeverity.INFO,
                message="未检测到可用网卡",
                current="无网卡",
                expected="网卡正常",
            ))

        # 找最快和最慢的网卡
        fastest = max(nics, key=lambda x: x["speed_mbps"])
        slowest = min(nics, key=lambda x: x["speed_mbps"])

        # 检查是否有慢速网卡
        slow_nics = [n for n in nics if n["speed_mbps"] < self.WARNING_SPEED]
        ideal_nics = [n for n in nics if n["speed_mbps"] >= self.IDEAL_SPEED]

        if slow_nics:
            worst = slow_nics[0]
            severity = CheckSeverity.CRITICAL if worst["speed_mbps"] <= self.SLOW_SPEED else CheckSeverity.WARNING
            return self._enhance_result_with_accuracy(CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=False,
                severity=severity,
                message=f"{worst['name']} 仅 {worst['speed_mbps']} Mbps（过低）",
                current=f"最快 {fastest['speed_mbps']} Mbps，最慢 {slowest['speed_mbps']} Mbps",
                expected=f"网卡速率 >= {self.IDEAL_SPEED} Mbps（千兆）",
                details={"nics": nics, "slow_nics": slow_nics},
            ))

        # 全部千兆以上
        return CheckResult(
            check_id=self.check_id,
            title=self.title,
            category=self.category,
            passed=True,
            severity=CheckSeverity.PASSED,
            message=f"{len(ideal_nics)}/{len(nics)} 网卡达到千兆以上",
            current=f"最快 {fastest['speed_mbps']} Mbps",
            expected=f">= {self.IDEAL_SPEED} Mbps",
            details={"nics": nics},
        )

    def _get_nic_speeds(self) -> list:
        """Get link speeds for all network interfaces"""
        nics = []

        # 方法1: ip link（通用 Linux）
        speeds = self._ip_link_speeds()
        nics.extend(speeds)

        # 方法2: ethtool（更准确）
        ethtool_speeds = self._ethtool_speeds()
        # 合并
        seen = {n["name"]: n for n in nics}
        for n in ethtool_speeds:
            if n["name"] in seen:
                # ethtool 数据更可靠，覆盖
                seen[n["name"]] = n
            else:
                seen[n["name"]] = n
        return list(seen.values())

    def _ip_link_speeds(self) -> list:
        """Get speeds via `ip link`"""
        nics = []
        try:
            result = subprocess.run(
                ["ip", "link", "show"],
                capture_output=True, text=True, errors="replace", timeout=5,
            )
            current_iface = None
            for line in result.stdout.splitlines():
                line = line.strip()
                # 新接口行: 1: eth0: <...> state ...
                match = re.match(r"^\d+:\s+(\S+):", line)
                if match:
                    name = match.group(1)
                    if name not in ("lo", "docker", "veth", "br-"):
                        current_iface = name
                # 速度行: speed XXXMb/s
                if current_iface:
                    speed_match = re.search(r"speed\s+(\d+)(Mbps|Mb/s)?", line)
                    if speed_match:
                        speed = int(speed_match.group(1))
                        if speed > 0:
                            nics.append({
                                "name": current_iface,
                                "speed_mbps": speed,
                                "source": "ip-link",
                            })
                        current_iface = None
        except Exception:
            pass
        return nics

    def _ethtool_speeds(self) -> list:
        """Get speeds via `ethtool`"""
        nics = []
        try:
            # 获取所有网卡名
            result = subprocess.run(
                ["ip", "link", "show"],
                capture_output=True, text=True, errors="replace", timeout=5,
            )
            ifnames = re.findall(r"^\d+:\s+(\S+):", result.stdout, re.MULTILINE)

            for ifname in ifnames:
                if ifname in ("lo", "docker0", "veth", "br-"):
                    continue
                speed = self._ethtool_speed(ifname)
                if speed is not None:
                    nics.append({
                        "name": ifname,
                        "speed_mbps": speed,
                        "source": "ethtool",
                    })
        except Exception:
            pass
        return nics

    def _ethtool_speed(self, ifname: str) -> Optional[int]:
        """Get speed for single interface via ethtool"""
        try:
            result = subprocess.run(
                ["ethtool", ifname],
                capture_output=True, text=True, errors="replace", timeout=5,
            )
            for line in result.stdout.splitlines():
                line = line.strip()
                if "Speed:" in line:
                    match = re.search(r"(\d+)(Mbps|Gbps)?", line)
                    if match:
                        speed = int(match.group(1))
                        unit = match.group(2) or "Mbps"
                        if unit == "Gbps":
                            speed *= 1000
                        return speed
        except Exception:
            pass
        return None
