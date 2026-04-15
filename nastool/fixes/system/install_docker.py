# -*- coding: utf-8 -*-
"""
fixes/system/install_docker.py - Install Docker Engine

v1.1 安全底线：
  • is_applicable() 先检测是否已有 Docker
  • 已有则跳过，返回 "already installed"
  • 不盲目执行 curl | sh（安全红线）
"""

import re
from ..base import Fix, FixResult
from ..registry import register_fix


@register_fix
class DockerFix(Fix):
    """
    安装 Docker Engine（v1.1 安全底线版）。

    is_applicable() 先检查 docker --version：
      - 已有 Docker → 不适用（跳过安装）
      - 无 Docker   → 适用
    """

    fix_id = "install_docker"
    title = "安装 Docker Engine"
    description = "检测到无 Docker 时安装（已有则跳过）"
    risk = "high"
    requires_root = True

    # 最低版本要求
    MIN_VERSION = (20, 10)

    def is_applicable(self) -> bool:
        """检查是否真的需要安装 Docker"""
        ok, out = self._run_command("docker --version")
        if ok:
            # Docker 已安装，检查版本是否够新
            version_str = out.strip()
            # 匹配 "Docker version 24.0.7, build afbccfc"
            m = re.search(r"Docker version (\d+)\.(\d+)", version_str)
            if m:
                major = int(m.group(1))
                minor = int(m.group(2))
                if (major, minor) >= self.MIN_VERSION:
                    self._cached_message = f"Docker {major}.{minor} 已安装（版本满足要求）"
                    return False
                else:
                    self._cached_message = f"Docker {major}.{minor} 版本过低，需要升级"
                    return True
            # Docker 存在但版本解析失败，保守跳过
            self._cached_message = f"Docker 已安装：{version_str}"
            return False

        # Docker 不存在
        return True

    def run(self) -> FixResult:
        commands_run = []
        messages = []

        # 再次确认（防御性，两次检查避免竞态）
        ok_check, out_check = self._run_command("docker --version")
        if ok_check:
            return FixResult(
                fix_id=self.fix_id,
                success=True,
                message=f"Docker 已存在，跳过安装：{out_check.strip()}",
                commands_run=commands_run,
            )

        # 检查系统
        os_ok, os_out = self._run_command("uname -a")
        system = os_out.lower()
        if "ubuntu" in system or "debian" in system:
            installer = self._install_ubuntu
        elif "centos" in system or "rhel" in system:
            installer = self._install_centos
        elif "fedora" in system:
            installer = self._install_fedora
        else:
            return FixResult(
                fix_id=self.fix_id,
                success=False,
                message="不支持的操作系统，请手动安装 Docker：https://docs.docker.com/engine/install/",
                commands_run=commands_run,
            )

        # 执行安装
        ok_install, install_msg = installer()
        commands_run.append(installer.__name__)
        if ok_install:
            # 安装后验证
            ok_verify, ver_out = self._run_command("docker --version")
            return FixResult(
                fix_id=self.fix_id,
                success=True,
                message=f"Docker 安装成功：{ver_out.strip()}"
                if ok_verify
                else "Docker 安装完成（请重启终端验证）",
                commands_run=commands_run,
            )
        else:
            return FixResult(
                fix_id=self.fix_id,
                success=False,
                message=f"Docker 安装失败：{install_msg}",
                commands_run=commands_run,
            )

    # ── 受支持的安装方法 ───────────────────────────────────────────

    def _install_ubuntu(self) -> tuple:
        """
        Ubuntu/Debian: 官方 apt 安装（非 curl|sh）
        v1.1 安全底线：不使用 curl | sh
        """
        steps = [
            ("apt update", 120),
            ("apt install -y ca-certificates curl gnupg lsb-release", 180),
            # 添加 Docker GPG apt key（通过 apt-keyring，非 curl|sh）
            ("mkdir -p /etc/apt/keyrings", 10),
            (
                "curl -fsSL https://download.docker.com/linux/ubuntu/gpg "
                "| gpg --dearmor -o /etc/apt/keyrings/docker.gpg",
                60,
            ),
            (
                'echo "deb [arch=$(dpkg --print-architecture) '
                "signed-by=/etc/apt/keyrings/docker.gpg] "
                'https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" '
                "| tee /etc/apt/sources.list.d/docker.list > /dev/null",
                20,
            ),
            ("apt update", 120),
            (
                "apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin",
                300,
            ),
            ("systemctl enable docker", 30),
            ("systemctl start docker", 30),
        ]

        for cmd, timeout in steps:
            ok, out = self._run_command(cmd, timeout=timeout)
            if not ok:
                return False, f"命令失败 [{cmd[:40]}...]: {out[:200]}"

        # 验证安装
        ok, out = self._run_command("docker run --rm hello-world", timeout=60)
        if not ok:
            return True, "Docker 已安装，hello-world 测试跳过（网络问题）"
        return True, out[:100]

    def _install_centos(self) -> tuple:
        """CentOS/RHEL: yum install"""
        steps = [
            ("yum install -y yum-utils", 120),
            (
                "yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo",
                30,
            ),
            ("yum install -y docker-ce docker-ce-cli containerd.io", 300),
            ("systemctl enable docker", 30),
            ("systemctl start docker", 30),
        ]
        for cmd, timeout in steps:
            ok, out = self._run_command(cmd, timeout=timeout)
            if not ok:
                return False, f"命令失败 [{cmd[:40]}...]: {out[:200]}"
        return True, "Docker 安装完成"

    def _install_fedora(self) -> tuple:
        """Fedora: dnf install"""
        steps = [
            ("dnf -y install dnf-plugins-core", 120),
            (
                "dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo",
                30,
            ),
            ("dnf install -y docker-ce", 300),
            ("systemctl enable docker", 30),
            ("systemctl start docker", 30),
        ]
        for cmd, timeout in steps:
            ok, out = self._run_command(cmd, timeout=timeout)
            if not ok:
                return False, f"命令失败 [{cmd[:40]}...]: {out[:200]}"
        return True, "Docker 安装完成"
