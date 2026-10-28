"""采集层解析器单测：不依赖真实硬件，任何平台都能跑。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nastool.collect import network as netmod
from nastool.collect import storage as stmod
from nastool.collect.network import _cidr_to_netmask, _parse_ip_br, parse_peer
from nastool.collect.storage import _parse_df_line, _size_to_gb
from nastool.connectors.ainas import _sanitize_id


# ── df 解析 ─────────────────────────────────────────────────
def test_parse_df_line_normal():
    line = "/dev/sda1 104857600 52428800 52428800 50% /volume1"
    d = _parse_df_line(line)
    assert d is not None
    assert d.device == "/dev/sda1"
    assert d.mountpoint == "/volume1"
    assert d.total_gb == 100.0
    assert d.use_percent == 50.0


def test_parse_df_line_mount_with_spaces():
    line = "/dev/sdb1 209715200 104857600 104857600 50% /mnt/my data"
    d = _parse_df_line(line)
    # df -kP 的挂载点允许有空格，解析要能把剩余部分整体当挂载点
    assert d is not None
    assert d.mountpoint.startswith("/mnt/my")
    assert d.total_gb == 200.0


def test_parse_df_line_garbage():
    assert _parse_df_line("") is None
    assert _parse_df_line("Filesystem 1K-blocks") is None
    assert _parse_df_line("a b c d e") is None


def test_size_to_gb():
    assert _size_to_gb("1.8T") == 1843.2
    assert _size_to_gb("500G") == 500.0
    assert _size_to_gb("200M") == 0.2
    assert _size_to_gb("") == 0.0


# ── mdstat ──────────────────────────────────────────────────
def test_mdstat_healthy(monkeypatch):
    content = (
        "Personalities : [raid1]\n"
        "md0 : active raid1 sda1[0] sdb1[1]\n"
        "      976630464 blocks super 1.2 [2/2] [UU]\n"
        "\n"
        "unused devices: <none>\n"
    )
    monkeypatch.setattr(stmod, "read_file", lambda *a, **k: content)
    raids = stmod.get_md_raid()
    assert len(raids) == 1
    assert raids[0].name == "md0"
    assert raids[0].level == "raid1"
    assert raids[0].members_total == 2
    assert raids[0].healthy is True


def test_mdstat_degraded(monkeypatch):
    content = (
        "md0 : active raid1 sda1[0] sdb1[1](F)\n"
        "      976630464 blocks super 1.2 [2/1] [U_]\n"
    )
    monkeypatch.setattr(stmod, "read_file", lambda *a, **k: content)
    raids = stmod.get_md_raid()
    assert len(raids) == 1
    assert raids[0].healthy is False
    assert raids[0].errors


def test_mdstat_missing(monkeypatch):
    monkeypatch.setattr(stmod, "read_file", lambda *a, **k: "")
    assert stmod.get_md_raid() == []


# ── 网络解析 ────────────────────────────────────────────────
def test_cidr_to_netmask():
    assert _cidr_to_netmask("24") == "255.255.255.0"
    assert _cidr_to_netmask("16") == "255.255.0.0"
    assert _cidr_to_netmask("32") == "255.255.255.255"
    assert _cidr_to_netmask("0") == "0.0.0.0"
    assert _cidr_to_netmask("abc") == ""
    assert _cidr_to_netmask("40") == ""


def test_parse_ip_br():
    out = (
        "lo               UNKNOWN        127.0.0.1/8 ::1/128\n"
        "eth0             UP             192.168.1.10/24 fe80::1/64\n"
        "docker0          DOWN           172.17.0.1/16\n"
    )
    ifaces = _parse_ip_br(out)
    names = [i.name for i in ifaces]
    assert "eth0" in names
    assert "lo" not in names
    assert "docker0" not in names
    eth = next(i for i in ifaces if i.name == "eth0")
    assert eth.ip == "192.168.1.10"
    assert eth.netmask == "255.255.255.0"
    assert eth.has_usable_ip()


def test_link_local_is_not_usable():
    iface = netmod.NetworkInterface(name="eth0", ip="169.254.3.4", up=True)
    assert iface.has_usable_ip() is False
    assert netmod.NetworkInterface(name="eth0", ip="10.0.0.2").has_usable_ip() is True


def test_parse_peer():
    assert parse_peer("192.168.1.10:445") == ("192.168.1.10", 445)
    assert parse_peer("nas.local") == ("nas.local", 443)
    assert parse_peer("[fe80::1]:80") == ("fe80::1", 80)


def test_sanitize_id():
    assert _sanitize_id("my nas / 01") == "my-nas---01"
    assert _sanitize_id("") == "device"
    assert len(_sanitize_id("x" * 300)) == 128
