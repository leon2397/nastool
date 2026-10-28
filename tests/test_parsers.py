"""解析器与纯函数单测：不依赖真实硬件，任何平台都能跑。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nastool.connectors.ainas import _sanitize_id
from nastool.core import storage
from nastool.core.network import _cidr_to_netmask, _parse_ip_br, parse_peer
from nastool.core.scoring import compute_score
from nastool.core.ai_accel import AIReport
from nastool.core.device import CpuInfo, DeviceReport, MemInfo
from nastool.core.network import NetworkInterface, NetworkReport
from nastool.core.platform_detect import PlatformReport
from nastool.core.services import ServicesReport
from nastool.core.storage import StorageReport


# ── df 解析 ─────────────────────────────────────────────────
def test_parse_df_line_normal():
    line = "/dev/sda1 104857600 52428800 52428800 50% /volume1"
    d = storage._parse_df_line(line)
    assert d is not None
    assert d.device == "/dev/sda1"
    assert d.mountpoint == "/volume1"
    assert d.total_gb == 100.0
    assert d.use_percent == 50.0


def test_parse_df_line_mount_with_spaces():
    # macOS / 特殊挂载点里带空格时，POSIX 输出依然是 6 列
    line = "/dev/disk1s1 1000 500 500 50% /Volumes/My Disk"
    d = storage._parse_df_line(line)
    assert d.total_gb == 0.0  # 1GB 以下按 KB 计算会很小，这里只验证不崩


def test_parse_df_line_garbage():
    assert storage._parse_df_line("") is None
    assert storage._parse_df_line("tmpfs 100 0 100 0% /dev/shm extra") is not None
    assert storage._parse_df_line("only two") is None


def test_size_to_gb():
    assert storage._size_to_gb("1.8T") == 1843.2
    assert storage._size_to_gb("500G") == 500.0
    assert storage._size_to_gb("200M") == 0.2


# ── mdstat 解析 ─────────────────────────────────────────────
def test_mdstat_healthy(monkeypatch):
    fake = """Personalities : [raid1] [raid6]
md0 : active raid1 sda1[0] sdb1[1]
      976630464 blocks super 1.2 [2/2] [UU]

unused devices: <none>"""
    monkeypatch.setattr(storage, "read_file", lambda *a, **k: fake)
    raids = storage.get_md_raid()
    assert len(raids) == 1
    r = raids[0]
    assert r.name == "md0"
    assert r.level == "raid1"
    assert r.healthy is True
    assert r.members_total == 2


def test_mdstat_degraded(monkeypatch):
    fake = """md0 : active raid1 sda1[0] sdb1[1](F)
      976630464 blocks super 1.2 [2/1] [U_]"""
    monkeypatch.setattr(storage, "read_file", lambda *a, **k: fake)
    raids = storage.get_md_raid()
    assert len(raids) == 1
    assert raids[0].healthy is False
    assert "降级" in raids[0].errors[0]


def test_mdstat_missing(monkeypatch):
    monkeypatch.setattr(storage, "read_file", lambda *a, **k: "")
    assert storage.get_md_raid() == []


# ── 网络解析 ────────────────────────────────────────────────
def test_cidr_to_netmask():
    assert _cidr_to_netmask("24") == "255.255.255.0"
    assert _cidr_to_netmask("16") == "255.255.0.0"
    assert _cidr_to_netmask("bad") == ""


def test_parse_ip_br():
    out = """lo               UNKNOWN        127.0.0.1/8 ::1/128
eth0             UP             192.168.1.50/24 fe80::1/64
docker0          DOWN           172.17.0.1/16"""
    ifaces = _parse_ip_br(out)
    names = [i.name for i in ifaces]
    assert "eth0" in names
    assert "lo" not in names
    assert "docker0" not in names
    eth0 = next(i for i in ifaces if i.name == "eth0")
    assert eth0.ip == "192.168.1.50"
    assert eth0.netmask == "255.255.255.0"
    assert eth0.up is True


def test_parse_peer():
    assert parse_peer("192.168.1.1:445") == ("192.168.1.1", 445)
    assert parse_peer("nas.local") == ("nas.local", 443)
    assert parse_peer("[fe80::1]:8080") == ("fe80::1", 8080)


def test_sanitize_id():
    assert _sanitize_id("my nas!") == "my-nas"
    assert _sanitize_id("") == "device"
    assert _sanitize_id("a" * 200) == "a" * 128


# ── 评分 ────────────────────────────────────────────────────
def _healthy_result_parts():
    device = DeviceReport(
        cpu=CpuInfo(model="Test CPU", cores=4, arch="x86_64"),
        memory=MemInfo(total_gb=16.0, available_gb=12.0, used_percent=25.0),
    )
    storage_rpt = StorageReport(
        target_path="/tmp", target_exists=True, is_dir=True, can_write=True,
        target_total_gb=100.0, target_free_gb=60.0, target_use_percent=40.0,
        speed_test_done=True, seq_write_mbps=200.0, seq_read_mbps=300.0, ok=True,
    )
    network = NetworkReport(
        interfaces=[NetworkInterface(name="eth0", ip="10.0.0.2", up=True, speed_mbps=1000)],
        dns_ok=True, gateway="10.0.0.1", gateway_reachable=True, ok=True,
    )
    services = ServicesReport(total_listening=3)
    platform = PlatformReport(kind="nas_appliance", vendor="Synology", product="DSM")
    ai = AIReport()
    return device, storage_rpt, network, services, platform, ai


def test_score_healthy_is_high():
    parts = _healthy_result_parts()
    score = compute_score(*parts)
    assert score.total >= 80
    assert score.grade in ("A", "B")
    assert len(score.findings) == 0 or score.findings[0].level != "critical"


def test_score_broken_storage_is_critical():
    device, storage_rpt, network, services, platform, ai = _healthy_result_parts()
    storage_rpt.can_write = False
    storage_rpt.errors = ["目标路径不可写"]
    storage_rpt.target_use_percent = 99.0
    score = compute_score(device, storage_rpt, network, services, platform, ai)
    assert any(f.level == "critical" for f in score.findings)
    assert score.total < 80


def test_score_range_always_valid():
    device, storage_rpt, network, services, platform, ai = _healthy_result_parts()
    # 全空输入也不应该超出 0-100
    empty = compute_score(DeviceReport(), StorageReport(), NetworkReport(),
                          ServicesReport(), PlatformReport(), AIReport())
    assert 0 <= empty.total <= 100
    full = compute_score(device, storage_rpt, network, services, platform, ai)
    assert 0 <= full.total <= 100
