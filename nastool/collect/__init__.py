"""
nastool/collect/__init__.py — 采集层总装

本层只做一件事：**把机器上的事实读出来**，不做任何「好还是坏」的判断。

这样分层的好处：
  - 采集失败不会变成错误结论（清单空 ≠ 服务没开）
  - 同一份事实可以被多个检查项复用，不重复执行命令
  - 报告里的「设备清单」直接来自这里，判定结果只来自 checks/

Facts.summary() 是给报告层用的展示结构：三个报告器共用一份，
避免过去「终端能显示、HTML 漏字段」的不一致。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .ai_accel import AIFacts, detect_ai_accelerator
from .device import DeviceFacts, get_device_info
from .network import NetworkFacts, collect_network
from .platform import PlatformFacts, PlatformKind, detect_platform
from .security import SecurityFacts, collect_security
from .services import ServicesFacts, collect_services
from .storage import StorageFacts, collect_storage

__all__ = [
    "Facts", "PlatformFacts", "DeviceFacts", "StorageFacts", "NetworkFacts",
    "ServicesFacts", "SecurityFacts", "AIFacts", "PlatformKind",
    "detect_platform", "get_device_info", "collect_storage",
    "collect_network", "collect_services", "collect_security",
    "detect_ai_accelerator",
]


@dataclass
class Facts:
    platform: PlatformFacts = field(default_factory=PlatformFacts)
    device: DeviceFacts = field(default_factory=DeviceFacts)
    storage: StorageFacts = field(default_factory=StorageFacts)
    network: NetworkFacts = field(default_factory=NetworkFacts)
    services: ServicesFacts = field(default_factory=ServicesFacts)
    security: SecurityFacts = field(default_factory=SecurityFacts)
    ai: AIFacts = field(default_factory=AIFacts)

    # ── 展示结构（三个报告器共用）──────────────────────────
    def summary(self) -> Dict[str, Any]:
        p, d, s = self.platform, self.device, self.storage
        n, sv, sec, ai = self.network, self.services, self.security, self.ai

        return {
            "platform": {
                "kind": p.kind,
                "vendor": p.vendor,
                "product": p.product,
                "version": p.version,
                "pretty_name": p.pretty_name,
                "arch": p.arch,
                "kernel": p.kernel,
                "hostname": p.hostname,
                "model": p.facts.get("model", "") or (
                    d.board.model if d.board.model and d.board.model != "未知" else ""),
                "in_container": p.in_container,
                "container_type": p.container_type,
                "is_root": p.is_root,
                "data_roots": list(p.data_roots),
            },
            "system": {
                "cpu": {
                    "model": d.cpu.model,
                    "cores": d.cpu.cores,
                    "physical_cores": d.cpu.physical_cores,
                    "freq_mhz": d.cpu.freq_mhz,
                    "arch": d.cpu.arch,
                },
                "memory": {
                    "total_gb": d.memory.total_gb,
                    "available_gb": d.memory.available_gb,
                    "used_percent": d.memory.used_percent,
                    "swap_total_gb": d.memory.swap_total_gb,
                    "swap_free_gb": d.memory.swap_free_gb,
                },
                "board": {
                    "manufacturer": d.board.manufacturer,
                    "model": d.board.model,
                    "serial": d.board.serial,
                    "os": d.board.os,
                    "os_version": d.board.os_version,
                    "uptime_hours": d.board.uptime_hours,
                },
                "virtualization": d.virtualization,
                "thermals": [
                    {"zone": t.zone, "type": t.zone_type, "temp_c": t.temp_c}
                    for t in d.thermals
                ],
            },
            "storage": {
                "target_path": s.target_path,
                "target_exists": s.target_exists,
                "can_write": s.can_write,
                "total_gb": s.target_total_gb,
                "free_gb": s.target_free_gb,
                "use_percent": s.target_use_percent,
                "speed": {
                    "done": s.speed_test_done,
                    "read_mbps": s.seq_read_mbps,
                    "write_mbps": s.seq_write_mbps,
                },
                "disks": [
                    {
                        "device": x.device, "mountpoint": x.mountpoint,
                        "fstype": x.fstype, "total_gb": x.total_gb,
                        "free_gb": x.free_gb, "use_percent": x.use_percent,
                        "inodes_use_percent": x.inodes_use_percent,
                        "readonly": x.readonly,
                    }
                    for x in s.disks
                ],
                "physical_disks": [
                    {"name": x.name, "size_gb": x.size_gb, "model": x.model,
                     "rotational": x.rotational}
                    for x in s.physical_disks
                ],
                "raids": [
                    {
                        "name": r.name, "kind": r.kind, "level": r.level,
                        "state": r.state, "members_total": r.members_total,
                        "members_active": r.members_active,
                        "rebuild_percent": r.rebuild_percent,
                        "healthy": r.healthy, "errors": list(r.errors),
                    }
                    for r in s.raids
                ],
                "smart": [
                    {
                        "device": x.device, "model": x.model, "healthy": x.healthy,
                        "temperature_c": x.temperature_c,
                        "power_on_hours": x.power_on_hours,
                        "reallocated_sectors": x.reallocated_sectors,
                        "pending_sectors": x.pending_sectors,
                        "message": x.message,
                    }
                    for x in s.smart
                ],
            },
            "network": {
                "interfaces": [
                    {
                        "name": i.name, "ip": i.ip, "netmask": i.netmask,
                        "mac": i.mac, "speed_mbps": i.speed_mbps,
                        "duplex": i.duplex, "up": i.up,
                        "is_wireless": i.is_wireless,
                        "usable_ip": i.has_usable_ip(),
                    }
                    for i in n.interfaces
                ],
                "gateway": n.gateway,
                "gateway_reachable": n.gateway_reachable,
                "dns_server": n.dns_server,
                "dns_ok": n.dns_ok,
                "internet_reachable": n.internet_reachable,
                "peers": [
                    {"label": p_.label, "host": p_.host, "port": p_.port,
                     "reachable": p_.reachable, "rtt_ms": p_.rtt_ms,
                     "error": p_.error}
                    for p_ in n.peers
                ],
            },
            "services": {
                "total_listening": sv.total_listening,
                "ephemeral_ports": sv.ephemeral_ports,
                "docker_available": sv.docker_available,
                "items": [
                    {"port": i.port, "name": i.name, "category": i.category,
                     "note": i.note, "process": i.process,
                     "bind_address": i.bind_address}
                    for i in sv.items
                ],
                "containers": [
                    {"name": c.name, "image": c.image, "status": c.status,
                     "ports": c.ports}
                    for c in sv.containers
                ],
                "processes": list(sv.processes),
            },
            "security": {
                "ssh": {
                    "found": sec.ssh.found,
                    "running": sec.ssh.running,
                    "port": sec.ssh.port,
                    "permit_root_login": sec.ssh.permit_root_login,
                    "password_auth": sec.ssh.password_auth,
                    "pubkey_auth": sec.ssh.pubkey_auth,
                },
                "firewall": {
                    "detected": list(sec.firewall.detected),
                    "active": sec.firewall.active,
                    "rule_count": sec.firewall.rule_count,
                    "detail": sec.firewall.detail,
                },
                "certs": [
                    {"path": c.path, "subject": c.subject, "issuer": c.issuer,
                     "not_after": c.not_after, "days_left": c.days_left,
                     "self_signed": c.self_signed, "error": c.error}
                    for c in sec.certs
                ],
                "smb_guest": sec.smb_guest,
                "smb_signing": sec.smb_signing,
                "nfs_no_root_squash": sec.nfs_no_root_squash,
                "ftp_anonymous": sec.ftp_anonymous,
                "fail2ban": sec.fail2ban,
                "ip_forward": sec.ip_forward,
            },
            "ai": {
                "best_chip_type": ai.best_chip_type,
                "hardware_accelerated": ai.hardware_accelerated,
                "inference_available": ai.inference_available,
                "inference_engine": ai.inference_engine,
                "inference_test_ms": ai.inference_test_ms,
                "devices": [
                    {"name": dv.name, "chip_type": dv.chip_type,
                     "vendor": dv.vendor, "available": dv.available,
                     "memory_total_mb": dv.memory_total_mb,
                     "detected_by": dv.detected_by}
                    for dv in ai.devices
                ],
                "notes": list(ai.notes),
            },
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.summary()
