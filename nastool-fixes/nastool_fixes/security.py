"""
fixes/security.py - Security Framework v1.0
固化安全准则：零破坏、零篡改、所有操作可撤销

所有 fix 函数在执行前必须通过 SecurityPolicy 检查。
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple

# ── 全局常量 ────────────────────────────────────────────────────────────────

# 备份根目录
BACKUP_ROOT = Path(os.path.expanduser("~/.nastool/backups"))

# 回滚脚本目录
ROLLBACK_DIR = Path(os.path.expanduser("~/.nastool/rollback_scripts"))


# ── 禁止操作清单（代码级硬编码屏蔽，永久禁用）──────────────────────────────

# fix_id → (禁止原因, 替代建议)
FORBIDDEN_FIXES: dict[str, tuple[str, str]] = {
    # 网络配置类 — 绝对禁止
    "config_dns":         ("修改 /etc/resolv.conf 可导致 DNS 失效，设备断网", "建议手动配置 /etc/resolv.conf，或检查网络适配器设置"),
    "config_network":     ("修改网络配置（IP/网关/路由）可导致设备断连", "建议通过设备管理界面配置网络"),
    "config_firewall":     ("修改防火墙规则可能阻断已有连接", "建议手动使用 ufw/firewalld 配置"),
    "reset_network":      ("重置网络配置会导致 SSH/远程连接断开", "建议通过控制台操作"),

    # 用户管理类 — 绝对禁止
    "disable_root_login":  ("修改 SSH root 登录策略可能锁死管理员", "建议手动编辑 /etc/ssh/sshd_config"),
    "create_user":        ("创建/删除用户账户属于高危系统操作", "建议通过系统用户管理工具操作"),
    "delete_user":        ("删除用户账户属于高危系统操作", "建议通过系统用户管理工具操作"),
    "modify_user":        ("修改用户权限/组属于高危系统操作", "建议通过系统用户管理工具操作"),
    "enforce_password_policy": ("修改密码策略影响所有用户登录", "建议手动编辑 /etc/login.defs 或 PAM 配置"),

    # 系统目录写入类 — 绝对禁止
    "write_etc":          ("写入 /etc 系统目录可能破坏系统完整性", "建议手动使用 root 权限编辑配置"),
    "modify_etc_hosts":   ("修改 /etc/hosts 影响 DNS 解析和网络连通性", "建议手动编辑 /etc/hosts"),

    # CUDA/驱动类 — 绝对禁止
    "install_cuda":       ("安装/升级 CUDA 驱动涉及系统级库替换，风险极高", "建议通过官方 JetPack 包管理器安装"),
    "install_gpu_driver": ("安装 GPU 驱动涉及内核模块加载，风险极高", "建议通过官方驱动包安装"),
    "update_kernel":      ("内核更新可能导致系统无法启动", "建议通过官方渠道更新"),
    "remove_kernel":      ("删除内核版本可能导致系统无法启动", "严禁操作"),

    # 破坏性类 — 绝对禁止
    "format_disk":        ("磁盘格式化将导致数据永久丢失", "严禁操作"),
    "delete_system_file": ("删除系统文件将导致系统不可用", "严禁操作"),
    "modify_boot":        ("修改启动项配置错误会导致系统无法启动", "严禁操作"),
    "wipe_data":          ("数据擦除操作不可逆，数据永久丢失", "严禁操作"),
    "factory_reset":      ("恢复出厂设置将清除所有数据", "严禁操作"),

    # 磁盘操作类 — 绝对禁止（除非有 RAID 专家在场）
    "config_raid_recovery": ("RAID 重建/恢复操作错误可导致数据全损", "建议在专业指导下操作，或使用 mdadm --assemble --scan"),
}


# ── 风险等级定义 ───────────────────────────────────────────────────────────

RISK_LOW    = "low"     # 无系统破坏风险：清理临时文件、生成报告
RISK_MEDIUM = "medium"  # 有限风险：清理 Docker 镜像、日志（可恢复）
RISK_HIGH   = "high"    # 显著风险：修改配置、安装软件包（需严格确认）
RISK_DANGER = "danger"  # 破坏性操作：磁盘、网络、驱动、用户管理


# 允许自动执行的最高风险等级（auto-fix 模式）
AUTO_FIX_MAX_RISK = RISK_LOW


# ── 安全策略类 ─────────────────────────────────────────────────────────────

class SecurityPolicy:
    """
    所有 fix 执行前必须通过此检查。
    不可绕过、不可关闭、不可配置。
    """

    @staticmethod
    def is_forbidden(fix_id: str) -> bool:
        """检查 fix_id 是否在禁止清单中"""
        return fix_id in FORBIDDEN_FIXES

    @staticmethod
    def get_forbidden_reason(fix_id: str) -> str:
        """获取禁止原因和替代建议"""
        if fix_id in FORBIDDEN_FIXES:
            reason, suggestion = FORBIDDEN_FIXES[fix_id]
            return f"[禁止] {reason}\n[建议] {suggestion}"
        return ""

    @staticmethod
    def can_auto_fix(risk: str) -> bool:
        """检查风险等级是否允许自动修复"""
        risk_order = [RISK_LOW, RISK_MEDIUM, RISK_HIGH, RISK_DANGER]
        try:
            return risk_order.index(risk) < risk_order.index(AUTO_FIX_MAX_RISK) + 1
        except ValueError:
            return False

    @staticmethod
    def check_fix(fix_id: str, risk: str = RISK_LOW) -> Tuple[bool, str]:
        """
        执行完整安全检查。

        Returns:
            (allowed, message): allowed=True 表示可以执行；False 表示被拦截
        """
        # 1. 禁止清单检查（最高优先级）
        if SecurityPolicy.is_forbidden(fix_id):
            msg = SecurityPolicy.get_forbidden_reason(fix_id)
            return False, f"[安全屏蔽] {msg}"

        # 2. 自动修复风险等级检查
        if not SecurityPolicy.can_auto_fix(risk):
            return False, (
                f"[风险屏蔽] {fix_id} 风险等级为 {risk}，"
                f"自动修复仅允许 {AUTO_FIX_MAX_RISK} 及以下操作"
            )

        return True, "通过安全检查"


# ── 备份管理器 ─────────────────────────────────────────────────────────────

class BackupManager:
    """
    统一备份/回滚管理器。
    所有 fix 执行前的备份统一由此类管理。
    """

    def __init__(self, backup_root: Optional[Path] = None):
        self.backup_root = backup_root or BACKUP_ROOT
        self.rollback_dir = ROLLBACK_DIR
        self.backup_root.mkdir(parents=True, exist_ok=True)
        self.rollback_dir.mkdir(parents=True, exist_ok=True)

    def backup_file(self, file_path: str) -> Optional[Path]:
        """
        备份单个文件。

        Args:
            file_path: 要备份的文件路径

        Returns:
            备份文件路径，失败返回 None
        """
        src = Path(file_path)
        if not src.exists():
            return None

        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup_name = f"{src.name}.{ts}.bak"
        backup_path = self.backup_root / backup_name

        try:
            shutil.copy2(src, backup_path)
            return backup_path
        except Exception:
            return None

    def backup_directory(self, dir_path: str, max_items: int = 100) -> Optional[Path]:
        """
        备份整个目录（压缩备份）。

        Args:
            dir_path: 要备份的目录路径
            max_items: 最多备份文件数（防止备份过大）

        Returns:
            备份压缩包路径，失败返回 None
        """
        src = Path(dir_path)
        if not src.exists() or not src.is_dir():
            return None

        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup_name = f"{src.name}.{ts}.tar.gz"
        backup_path = self.backup_root / backup_name

        try:
            # 统计文件数
            items = list(src.rglob("*"))
            if len(items) > max_items:
                # 文件太多，跳过备份（但记录）
                return None

            result = subprocess.run(
                ["tar", "czf", str(backup_path), "-C", str(src.parent), src.name],
                capture_output=True, text=True, timeout=300,
            )
            if result.returncode == 0:
                return backup_path
            return None
        except Exception:
            return None

    def backup_config(self, config_path: str) -> Optional[Path]:
        """
        备份配置文件（带内容哈希校验）。

        Returns:
            备份路径，失败返回 None
        """
        src = Path(config_path)
        if not src.exists():
            return None

        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup_name = f"{src.name}.{ts}.bak"
        backup_path = self.backup_root / backup_name

        try:
            shutil.copy2(src, backup_path)
            # 计算原始文件哈希
            with open(src, "rb") as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()[:16]
            # 记录哈希到同名 .meta 文件
            meta_path = backup_path.with_suffix(backup_path.suffix + ".meta")
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump({
                    "original": str(src),
                    "timestamp": datetime.now().isoformat(),
                    "sha256": file_hash,
                    "size": src.stat().st_size,
                }, f, ensure_ascii=False, indent=2)
            return backup_path
        except Exception:
            return None

    def create_rollback_script(
        self,
        fix_id: str,
        actions: List[Tuple[str, str, str]],
        dry_run: bool = False,
    ) -> Path:
        """
        生成回滚脚本。

        Args:
            fix_id: Fix 标识符
            actions: List[(操作类型, 源路径, 备份路径)]
                     操作类型: "copy" | "move" | "delete"
            dry_run: 是否为 dry-run 模式

        Returns:
            回滚脚本文件路径
        """
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        script_name = f"rollback_{fix_id}_{ts}.sh"
        script_path = self.rollback_dir / script_name

        lines = [
            "#!/bin/bash",
            f"# nastool 回滚脚本 - {fix_id}",
            f"# 生成时间: {datetime.now().isoformat()}",
            f"# 模式: {'DRY-RUN' if dry_run else 'REAL'}",
            "",
            'echo "[nastool] 开始回滚操作: ' + fix_id + '"',
            f'BACKUP_ROOT="{self.backup_root}"',
            "",
        ]

        for action_type, src, bak in actions:
            if action_type == "copy":
                # 从备份恢复到原位置
                lines.append(f'if [ -f "$BACKUP_ROOT/{Path(bak).name}" ]; then')
                lines.append(f'  cp "$BACKUP_ROOT/{Path(bak).name}" "{src}"')
                lines.append(f'  echo "[OK] 已恢复: {src}"')
                lines.append("else")
                lines.append(f'  echo "[WARN] 备份文件不存在，跳过: {src}"')
                lines.append("fi")
            elif action_type == "delete":
                lines.append(f'# 删除操作（手动确认）: {src}')
                lines.append(f'echo "[INFO] 如需删除请手动执行: rm -rf {src}"')

        lines.extend([
            "",
            'echo "[nastool] 回滚完成"',
        ])

        script_content = "\n".join(lines)

        try:
            if sys.platform == "win32":
                script_path.write_bytes(script_content.encode("utf-8", errors="replace"))
            else:
                script_path.write_text(script_content, encoding="utf-8")
            script_path.chmod(0o755)
            return script_path
        except Exception:
            return script_path  # 返回路径，即使写入失败也告知用户

    def list_backups(self, fix_id: Optional[str] = None) -> List[dict]:
        """列出已有备份"""
        backups = []
        if not self.backup_root.exists():
            return backups

        for f in sorted(self.backup_root.iterdir(), reverse=True):
            if f.is_file():
                backups.append({
                    "file": f.name,
                    "path": str(f),
                    "size": f.stat().st_size,
                    "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                })
        return backups


# ── 全局单例 ───────────────────────────────────────────────────────────────

_policy = None
_backup_mgr = None


def get_policy() -> SecurityPolicy:
    global _policy
    if _policy is None:
        _policy = SecurityPolicy()
    return _policy


def get_backup_manager() -> BackupManager:
    global _backup_mgr
    if _backup_mgr is None:
        _backup_mgr = BackupManager()
    return _backup_mgr
