"""
fixes/fix_recommendations.py - Check -> Fix 轻量映射表 + 不可修复项标注

v5.1.0  重构 --fix 为"智能推荐"模式
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set

# ─────────────────────────────────────────────────────────────────────────────
# Check -> Fix 映射表（一个 check 可对应多个 fix）
#  key: check_id
#  value: (fix_id, FixRecommendation)
# ─────────────────────────────────────────────────────────────────────────────

FIX_RECOMMENDATIONS: Dict[str, List[dict]] = {
    # ── Python 环境 ───────────────────────────────────────────────
    "python_version": [
        {
            "fix_id": "install_python",
            "action": "升级 Python 版本",
            "auto_applicable": True,
        }
    ],
    "pip_installed": [
        {
            "fix_id": "install_python",
            "action": "安装 pip",
            "auto_applicable": True,
        }
    ],

    # ── Docker ────────────────────────────────────────────────────
    "docker_info": [
        {
            "fix_id": "install_docker",
            "action": "安装 / 修复 Docker",
            "auto_applicable": True,
        }
    ],
    "docker_compose_installed": [
        {
            "fix_id": "install_docker",
            "action": "安装 Docker Compose",
            "auto_applicable": True,
        }
    ],
    "docker_images": [
        {
            "fix_id": "cleanup_docker_images",
            "action": "清理未使用的 Docker 镜像",
            "auto_applicable": True,
        }
    ],

    # ── 日志 / 存储清理 ───────────────────────────────────────────
    "logrotate_config": [
        {
            "fix_id": "setup_logrotate",
            "action": "配置日志轮转",
            "auto_applicable": True,
        }
    ],
    "log_disk_usage": [
        {
            "fix_id": "cleanup_logs",
            "action": "清理系统日志",
            "auto_applicable": True,
        }
    ],
    "tmp_space": [
        {
            "fix_id": "cleanup_tmp_space",
            "action": "清理临时文件",
            "auto_applicable": True,
        }
    ],

    # ── 路径 / 磁盘 ───────────────────────────────────────────────
    "storage_path": [
        {
            "fix_id": "create_paths",
            "action": "创建缺失的存储路径",
            "auto_applicable": True,
        }
    ],
    "disk_space": [
        {
            "fix_id": "cleanup_docker_images",
            "action": "清理 Docker 镜像释放空间",
            "auto_applicable": True,
        },
        {
            "fix_id": "cleanup_logs",
            "action": "清理系统日志",
            "auto_applicable": True,
        },
        {
            "fix_id": "cleanup_tmp_space",
            "action": "清理临时文件",
            "auto_applicable": True,
        },
    ],

    # ── RAID ──────────────────────────────────────────────────────
    "raid_status": [
        {
            "fix_id": "config_raid_recovery",
            "action": "查看 RAID 阵列状态并尝试恢复",
            "auto_applicable": True,
            "warning": "RAID 操作有风险，请在人工确认后再执行",
        }
    ],

    # ── 网络 / DNS ────────────────────────────────────────────────
    "dns_coverage": [
        {
            "fix_id": "config_dns",
            "action": "配置多个公共 DNS 服务器",
            "auto_applicable": True,
        }
    ],

    # ── CUDA / AI ─────────────────────────────────────────────────
    "cuda_available": [
        {
            "fix_id": "install_cuda",
            "action": "安装 / 升级 CUDA Toolkit",
            "auto_applicable": True,
        }
    ],
    "gpu_detected": [
        {
            "fix_id": "install_cuda",
            "action": "检查 GPU 驱动并尝试修复",
            "auto_applicable": True,
        }
    ],

    # ── 安全 ──────────────────────────────────────────────────────
    "ssh_root_login": [
        {
            "fix_id": "disable_root_login",
            "action": "禁用 SSH root 直接登录",
            "auto_applicable": True,
            "warning": "[!] 操作有中断 SSH 连接的风险，请确认有备用管理员账号",
        }
    ],
    "ssh_fail2ban": [
        {
            "fix_id": "enable_fail2ban",
            "action": "安装并启用 fail2ban 防暴力破解",
            "auto_applicable": True,
        }
    ],
    "weak_password": [
        {
            "fix_id": "enforce_password_policy",
            "action": "强制修改弱密码策略",
            "auto_applicable": True,
            "warning": "[!] 密码策略变更会影响所有用户，请提前通知",
        }
    ],
    "ssl_expiry": [
        {
            "fix_id": "renew_ssl_cert",
            "action": "续期 SSL 证书",
            "auto_applicable": True,
        }
    ],

    # ── UPS ────────────────────────────────────────────────────────
    "ups_status": [
        {
            "fix_id": "config_ups_shutdown",
            "action": "配置 UPS 自动关机",
            "auto_applicable": True,
        }
    ],
}


# ─────────────────────────────────────────────────────────────────────────────
# 不可自动修复项的分类标注（需人工处理）
# ─────────────────────────────────────────────────────────────────────────────

MANUAL_CATEGORIES: Dict[str, dict] = {
    "hardware": {
        "label": "🖥 硬件问题",
        "description": "需要物理检查或更换硬件，自动化修复有风险",
        "examples": ["smart_health", "raid_status", "disk_space", "usb_power"],
    },
    "network": {
        "label": "🌐 网络问题",
        "description": "网络故障需人工排查线缆、路由器、ISP 等",
        "examples": ["internet_connectivity", "dns_resolve", "nas_backend"],
    },
    "configuration": {
        "label": "⚙ 配置问题",
        "description": "服务配置错误需人工审慎修改",
        "examples": ["service_running", "smb_service", "nfs_service"],
    },
    "security": {
        "label": "🔒 安全配置",
        "description": "安全配置变更需评估业务影响，不建议盲目自动执行",
        "examples": ["firewall_enabled", "ssh_protocol", "ssh_root_login"],
    },
    "driver": {
        "label": "🔌 驱动问题",
        "description": "驱动问题需下载特定版本，建议人工处理",
        "examples": ["gpu_detected", "cuda_available", "paddle_installed"],
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────────────────────────────────────

def get_recommendations(check_id: str) -> List[dict]:
    """返回某 check_id 对应的修复建议列表（可能为空）"""
    return FIX_RECOMMENDATIONS.get(check_id, [])


def get_manual_category(check_id: str) -> Optional[dict]:
    """返回某 check_id 所属的人工处理类别"""
    for category in MANUAL_CATEGORIES.values():
        if check_id in category["examples"]:
            return category
    return None


def has_fix(check_id: str) -> bool:
    """该 check 是否有任何 fix 建议"""
    return check_id in FIX_RECOMMENDATIONS


def get_all_recommended_fix_ids() -> Set[str]:
    """返回映射表中所有涉及到的 fix_id"""
    result = set()
    for recs in FIX_RECOMMENDATIONS.values():
        for rec in recs:
            result.add(rec["fix_id"])
    return result


def summarize_check(check_id: str, severity: str, result_message: str) -> dict:
    """
    生成单个检查项的修复摘要，
    供交互式 --fix 流程展示使用。
    """
    recs = get_recommendations(check_id)
    manual_cat = get_manual_category(check_id)
    has_auto = any(r.get("auto_applicable") for r in recs)

    return {
        "check_id": check_id,
        "severity": severity,
        "message": result_message,
        "has_recommendation": len(recs) > 0,
        "has_auto_fix": has_auto,
        "manual_category": manual_cat,
        "recommendations": recs,
    }
