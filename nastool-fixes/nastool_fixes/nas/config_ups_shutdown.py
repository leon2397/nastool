# -*- coding: utf-8 -*-
"""
fixes/nas/config_ups_shutdown.py - Configure UPS graceful shutdown
对应检测: checks/nas/ups_status.py
风险: medium | requires_root: True
"""

from ..base import Fix, FixResult
from ..registry import register_fix


@register_fix
class ConfigUPSShutdownFix(Fix):
    """配置UPS断电自动关机保护"""

    fix_id = "config_ups_shutdown"
    title = "配置UPS断电关机"
    description = "安装并配置NUT (Network UPS Tools)，实现UPS电量耗尽时自动安全关机"
    risk = "medium"
    requires_root = True

    UPS_CONFIG = """\
# NUT client configuration
MODE=standalone
MONITOR ups@localhost 1 monuser secret slave
"""

    def is_applicable(self) -> bool:
        """检查NUT是否已配置"""
        import os
        nut_conf = "/etc/nut/nut.conf"
        if os.path.exists(nut_conf):
            ok, out = self._run_command(f"grep '^MODE=' {nut_conf}")
            if ok and "standalone" in out:
                return False
        return True

    def run(self) -> FixResult:
        commands_run = []

        os_release_out, _ = self._run_command("cat /etc/os-release")
        system = "unknown"
        if "ubuntu" in os_release_out.lower() or "debian" in os_release_out.lower():
            system = "debian"
        elif "centos" in os_release_out.lower() or "rhel" in os_release_out.lower():
            system = "centos"

        if system == "unknown":
            return FixResult(
                fix_id=self.fix_id,
                success=False,
                message="不支持的操作系统，请手动配置NUT",
                commands_run=commands_run,
            )

        # 安装 NUT
        if system == "debian":
            steps = [
                ("apt update", 120),
                ("apt install -y nut", 180),
            ]
        else:
            steps = [
                ("yum install -y nut", 180),
            ]

        for cmd, timeout in steps:
            ok, out = self._run_command(cmd, timeout=timeout)
            commands_run.append(cmd)
            if not ok:
                return FixResult(
                    fix_id=self.fix_id,
                    success=False,
                    message=f"NUT安装失败: {out[:200]}",
                    commands_run=commands_run,
                )

        # 写入基本配置
        nut_conf = "/etc/nut/nut.conf"
        try:
            with open(nut_conf, "w") as f:
                f.write("MODE=standalone\n")
            commands_run.append(f"write {nut_conf}")

            with open("/etc/nut/upsmon.conf", "a") as f:
                f.write("\nMONITOR ups@localhost 1 monuser secret slave\n")
            commands_run.append("write /etc/nut/upsmon.conf")

        except Exception as e:
            return FixResult(
                fix_id=self.fix_id,
                success=False,
                message=f"写入NUT配置失败: {e}",
                commands_run=commands_run,
            )

        # 启用并启动
        ok_enable, _ = self._run_command("systemctl enable nut-client")
        commands_run.append("systemctl enable nut-client")

        ok_start, _ = self._run_command("systemctl start nut-client")
        commands_run.append("systemctl start nut-client")

        return FixResult(
            fix_id=self.fix_id,
            success=True,
            message="NUT UPS客户端已配置。请根据实际UPS型号编辑/etc/nut/ups.conf配置UPS设备。",
            commands_run=commands_run,
        )
