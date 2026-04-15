# -*- coding: utf-8 -*-
"""
core/upnp_scanner.py — UPnP/SSDP 局域网设备发现
通用发现协议，支持 NAS/路由器/打印机/媒体服务器等
"""

import socket
import struct
import re
import time
import threading
import xml.etree.ElementTree as ET
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable
from enum import Enum


class DeviceType(Enum):
    """UPnP 设备类型"""

    ROUTER = "router"
    NAS = "nas"
    PRINTER = "printer"
    MEDIA_SERVER = "media_server"
    MEDIA_RENDERER = "media_renderer"
    SMART_TV = "smart_tv"
    GAME_CONSOLE = "game_console"
    IOT_DEVICE = "iot_device"
    UNKNOWN = "unknown"


@dataclass
class UPnPDevice:
    """UPnP 设备信息"""

    usn: str = ""  # Unique Service Name
    location: str = ""  # 设备描述 XML URL
    server: str = ""  # 服务器标识
    st: str = ""  # Search Target
    cache_control: str = ""  # 缓存控制

    # 从 XML 解析
    friendly_name: str = ""
    manufacturer: str = ""
    model_name: str = ""
    model_number: str = ""
    serial_number: str = ""
    device_type: str = ""
    services: List[str] = field(default_factory=list)

    # 网络信息
    ip: str = ""
    port: int = 0
    mac: str = ""

    # 分类
    category: DeviceType = DeviceType.UNKNOWN

    # 发现时间
    discovered_at: str = ""


@dataclass
class UPnPScanResult:
    """UPnP 扫描结果"""

    timestamp: str
    devices: List[UPnPDevice] = field(default_factory=list)
    total: int = 0
    scan_time_ms: int = 0
    ok: bool = True


# ══════════════════════════════════════════════════════════════════
# SSDP 协议常量
# ══════════════════════════════════════════════════════════════════

SSDP_ADDR = "239.255.255.250"
SSDP_PORT = 1900
SSDP_MX = 3  # 最大等待时间（秒）

# 搜索目标
SSDP_SEARCH_ALL = "ssdp:all"
SSDP_SEARCH_ROOT = "upnp:rootdevice"
SSDP_SEARCH_WAN = "urn:schemas-upnp-org:device:WANDevice:1"
SSDP_SEARCH_MEDIA_SERVER = "urn:schemas-upnp-org:device:MediaServer:1"
SSDP_SEARCH_MEDIA_RENDERER = "urn:schemas-upnp-org:device:MediaRenderer:1"
SSDP_SEARCH_PRINTER = "urn:schemas-upnp-org:device:Printer:1"

# 设备类型识别规则
DEVICE_TYPE_PATTERNS = {
    DeviceType.ROUTER: [
        "WANDevice",
        "WANConnectionDevice",
        "InternetGatewayDevice",
        "router",
        "gateway",
    ],
    DeviceType.NAS: [
        "NAS",
        "FileServer",
        "Storage",
        "Synology",
        "QNAP",
        "ASUSTOR",
        "Buffalo",
        "D-Link DNS",
    ],
    DeviceType.PRINTER: ["Printer", "PrinterBasic", "PrintBasic"],
    DeviceType.MEDIA_SERVER: ["MediaServer", "ContentDirectory"],
    DeviceType.MEDIA_RENDERER: ["MediaRenderer", "AVTransport", "RenderingControl"],
    DeviceType.SMART_TV: ["TV", "SmartTV", "Samsung", "LG", "Sony", "Vizio"],
    DeviceType.GAME_CONSOLE: ["Xbox", "PlayStation", "Nintendo"],
    DeviceType.IOT_DEVICE: ["IoT", "Smart", "Home", "Hub", "Sensor"],
}


# ══════════════════════════════════════════════════════════════════
# SSDP 发现
# ══════════════════════════════════════════════════════════════════


def create_msearch_packet(search_target: str = SSDP_SEARCH_ALL, mx: int = SSDP_MX) -> bytes:
    """
    创建 M-SEARCH 请求包

    Args:
        search_target: 搜索目标
        mx: 最大等待时间

    Returns:
        SSDP M-SEARCH 请求字节
    """
    request = (
        f"M-SEARCH * HTTP/1.1\r\n"
        f"HOST: {SSDP_ADDR}:{SSDP_PORT}\r\n"
        f'MAN: "ssdp:discover"\r\n'
        f"MX: {mx}\r\n"
        f"ST: {search_target}\r\n"
        f"\r\n"
    )
    return request.encode("utf-8")


def parse_ssdp_response(data: bytes, addr: tuple) -> Optional[UPnPDevice]:
    """
    解析 SSDP 响应

    Args:
        data: 响应数据
        addr: 发送者地址 (ip, port)

    Returns:
        UPnPDevice 或 None
    """
    try:
        text = data.decode("utf-8", errors="ignore")

        # 检查是否是 SSDP 响应
        if not text.startswith("HTTP/1.1 200 OK") and not text.startswith("NOTIFY"):
            return None

        device = UPnPDevice()
        device.ip = addr[0]
        device.port = addr[1]
        device.discovered_at = datetime.now().isoformat()

        # 解析头部
        headers = {}
        for line in text.split("\r\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                headers[key.strip().lower()] = value.strip()

        device.usn = headers.get("usn", "")
        device.location = headers.get("location", "")
        device.server = headers.get("server", "")
        device.st = headers.get("st", "")
        device.cache_control = headers.get("cache-control", "")

        # 验证必要字段
        if not device.location:
            return None

        return device

    except Exception as e:
        return None


def ssdp_discover(
    search_target: str = SSDP_SEARCH_ALL,
    timeout: float = 5.0,
    callback: Optional[Callable[[UPnPDevice], None]] = None,
) -> List[UPnPDevice]:
    """
    SSDP 发现设备

    Args:
        search_target: 搜索目标
        timeout: 超时时间（秒）
        callback: 发现设备时的回调函数

    Returns:
        发现的设备列表
    """
    devices = []
    seen_locations = set()

    # 创建 UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # 绑定到所有接口
    try:
        sock.bind(("0.0.0.0", 0))
    except Exception as e:
        sock.bind(("", 0))

    # 设置超时
    sock.settimeout(timeout)

    # 发送 M-SEARCH
    request = create_msearch_packet(search_target)
    sock.sendto(request, (SSDP_ADDR, SSDP_PORT))

    # 接收响应
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            data, addr = sock.recvfrom(4096)
            device = parse_ssdp_response(data, addr)

            if device and device.location not in seen_locations:
                seen_locations.add(device.location)
                devices.append(device)

                if callback:
                    callback(device)

        except socket.timeout:
            break
        except Exception as e:
            continue

    sock.close()
    return devices


# ══════════════════════════════════════════════════════════════════
# 设备描述 XML 解析
# ══════════════════════════════════════════════════════════════════


def fetch_device_description(device: UPnPDevice, timeout: float = 5.0) -> bool:
    """
    获取设备描述 XML

    Args:
        device: UPnP 设备
        timeout: 超时时间

    Returns:
        是否成功
    """
    if not device.location:
        return False

    try:
        import urllib.request

        # 解析 URL
        from urllib.parse import urlparse

        parsed = urlparse(device.location)

        # 更新 IP 和端口
        if not device.ip or device.ip == "0.0.0.0":
            device.ip = parsed.hostname
        if not device.port:
            device.port = parsed.port or 80

        # 获取 XML
        request = urllib.request.Request(device.location)
        request.add_header("User-Agent", "nastool UPnP Scanner")

        with urllib.request.urlopen(request, timeout=timeout) as response:
            xml_data = response.read().decode("utf-8", errors="ignore")

        # 解析 XML
        return parse_device_xml(device, xml_data)

    except Exception as e:
        return False


def parse_device_xml(device: UPnPDevice, xml_data: str) -> bool:
    """
    解析设备描述 XML

    Args:
        device: UPnP 设备
        xml_data: XML 数据

    Returns:
        是否成功
    """
    try:
        # 移除命名空间（简化解析）
        xml_data = re.sub(r'xmlns="[^"]+"', "", xml_data)
        xml_data = re.sub(r'xmlns:xsi="[^"]+"', "", xml_data)

        root = ET.fromstring(xml_data)

        # 查找 device 元素
        device_elem = root.find(".//device")
        if device_elem is None:
            device_elem = root.find("device")

        if device_elem is None:
            return False

        # 解析设备信息
        def get_text(elem, tag):
            child = elem.find(tag)
            return child.text.strip() if child is not None and child.text else ""

        device.friendly_name = get_text(device_elem, "friendlyName")
        device.manufacturer = get_text(device_elem, "manufacturer")
        device.model_name = get_text(device_elem, "modelName")
        device.model_number = get_text(device_elem, "modelNumber")
        device.serial_number = get_text(device_elem, "serialNumber")
        device.device_type = get_text(device_elem, "deviceType")

        # 解析服务列表
        service_list = device_elem.find("serviceList")
        if service_list is not None:
            for service in service_list.findall("service"):
                service_type = get_text(service, "serviceType")
                if service_type:
                    device.services.append(service_type)

        # 分类设备
        device.category = classify_device(device)

        return True

    except Exception as e:
        return False


def classify_device(device: UPnPDevice) -> DeviceType:
    """
    分类设备类型

    Args:
        device: UPnP 设备

    Returns:
        设备类型
    """
    # 组合所有文本用于匹配
    text = " ".join(
        [
            device.friendly_name,
            device.manufacturer,
            device.model_name,
            device.device_type,
            device.server,
            " ".join(device.services),
        ]
    ).lower()

    # 匹配规则
    for device_type, patterns in DEVICE_TYPE_PATTERNS.items():
        for pattern in patterns:
            if pattern.lower() in text:
                return device_type

    return DeviceType.UNKNOWN


# ══════════════════════════════════════════════════════════════════
# 综合扫描
# ══════════════════════════════════════════════════════════════════


def scan_upnp(
    search_targets: List[str] = None,
    timeout: float = 5.0,
    fetch_xml: bool = True,
    callback: Optional[Callable[[UPnPDevice], None]] = None,
) -> UPnPScanResult:
    """
    主入口：UPnP 扫描

    Args:
        search_targets: 搜索目标列表（默认搜索所有）
        timeout: 超时时间（秒）
        fetch_xml: 是否获取设备描述 XML
        callback: 发现设备时的回调函数

    Returns:
        扫描结果
    """
    start_time = time.time()

    result = UPnPScanResult(timestamp=datetime.now().isoformat())

    # 默认搜索目标
    if not search_targets:
        search_targets = [SSDP_SEARCH_ROOT, SSDP_SEARCH_ALL]

    # 扫描
    all_devices = []

    for target in search_targets:
        devices = ssdp_discover(target, timeout, callback)
        all_devices.extend(devices)

    # 去重
    seen = set()
    for device in all_devices:
        key = device.location or device.usn
        if key not in seen:
            seen.add(key)

            # 获取设备描述
            if fetch_xml and device.location:
                fetch_device_description(device)

            result.devices.append(device)

    # 排序
    result.devices.sort(key=lambda d: (d.category.value, d.friendly_name or d.ip))

    result.total = len(result.devices)
    result.scan_time_ms = int((time.time() - start_time) * 1000)

    return result


def scan_nas_devices(timeout: float = 5.0) -> List[UPnPDevice]:
    """
    专门扫描 NAS 设备

    Args:
        timeout: 超时时间

    Returns:
        NAS 设备列表
    """
    result = scan_upnp(search_targets=[SSDP_SEARCH_ALL], timeout=timeout, fetch_xml=True)

    return [d for d in result.devices if d.category == DeviceType.NAS]


def scan_routers(timeout: float = 5.0) -> List[UPnPDevice]:
    """
    专门扫描路由器

    Args:
        timeout: 超时时间

    Returns:
        路由器列表
    """
    result = scan_upnp(
        search_targets=[SSDP_SEARCH_WAN, SSDP_SEARCH_ROOT], timeout=timeout, fetch_xml=True
    )

    return [d for d in result.devices if d.category == DeviceType.ROUTER]


def scan_media_devices(timeout: float = 5.0) -> List[UPnPDevice]:
    """
    专门扫描媒体设备

    Args:
        timeout: 超时时间

    Returns:
        媒体设备列表
    """
    result = scan_upnp(
        search_targets=[SSDP_SEARCH_MEDIA_SERVER, SSDP_SEARCH_MEDIA_RENDERER],
        timeout=timeout,
        fetch_xml=True,
    )

    return [
        d
        for d in result.devices
        if d.category in [DeviceType.MEDIA_SERVER, DeviceType.MEDIA_RENDERER]
    ]


# ══════════════════════════════════════════════════════════════════
# UPnP 端口映射（可选）
# ══════════════════════════════════════════════════════════════════


def get_external_ip(device: UPnPDevice) -> Optional[str]:
    """
    通过 UPnP 获取外部 IP

    Args:
        device: 路由器设备

    Returns:
        外部 IP 或 None
    """
    # 查找 WANIPConnection 服务
    service = None
    for s in device.services:
        if "WANIPConnection" in s or "WANPPPConnection" in s:
            service = s
            break

    if not service:
        return None

    try:
        import urllib.request
        from urllib.parse import urlparse

        # 构建 SOAP 请求
        parsed = urlparse(device.location)
        control_url = f"http://{parsed.hostname}:{parsed.port or 80}/upnp/control/WANIPConnection"

        soap_body = (
            '<?xml version="1.0"?>'
            '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
            's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
            "<s:Body>"
            '<u:GetExternalIPAddress xmlns:u="urn:schemas-upnp-org:service:WANIPConnection:1"/>'
            "</s:Body>"
            "</s:Envelope>"
        )

        request = urllib.request.Request(control_url, data=soap_body.encode("utf-8"))
        request.add_header("Content-Type", 'text/xml; charset="utf-8"')
        request.add_header(
            "SOAPAction", '"urn:schemas-upnp-org:service:WANIPConnection:1#GetExternalIPAddress"'
        )

        with urllib.request.urlopen(request, timeout=5) as response:
            xml_data = response.read().decode("utf-8")

            # 解析响应
            match = re.search(r"<NewExternalIPAddress>([^<]+)</NewExternalIPAddress>", xml_data)
            if match:
                return match.group(1)

    except Exception as e:
        pass  # TODO: 添加日志

    return None


def add_port_mapping(
    device: UPnPDevice,
    external_port: int,
    internal_port: int,
    internal_client: str,
    protocol: str = "TCP",
    description: str = "nastool",
) -> bool:
    """
    通过 UPnP 添加端口映射

    Args:
        device: 路由器设备
        external_port: 外部端口
        internal_port: 内部端口
        internal_client: 内部客户端 IP
        protocol: 协议（TCP/UDP）
        description: 描述

    Returns:
        是否成功
    """
    # 查找 WANIPConnection 服务
    service = None
    for s in device.services:
        if "WANIPConnection" in s:
            service = s
            break

    if not service:
        return False

    try:
        import urllib.request
        from urllib.parse import urlparse

        parsed = urlparse(device.location)
        control_url = f"http://{parsed.hostname}:{parsed.port or 80}/upnp/control/WANIPConnection"

        soap_body = (
            f'<?xml version="1.0"?>'
            f'<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
            f's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
            f"<s:Body>"
            f'<u:AddPortMapping xmlns:u="urn:schemas-upnp-org:service:WANIPConnection:1">'
            f"<NewRemoteHost></NewRemoteHost>"
            f"<NewExternalPort>{external_port}</NewExternalPort>"
            f"<NewProtocol>{protocol}</NewProtocol>"
            f"<NewInternalPort>{internal_port}</NewInternalPort>"
            f"<NewInternalClient>{internal_client}</NewInternalClient>"
            f"<NewEnabled>1</NewEnabled>"
            f"<NewPortMappingDescription>{description}</NewPortMappingDescription>"
            f"<NewLeaseDuration>0</NewLeaseDuration>"
            f"</u:AddPortMapping>"
            f"</s:Body>"
            f"</s:Envelope>"
        )

        request = urllib.request.Request(control_url, data=soap_body.encode("utf-8"))
        request.add_header("Content-Type", 'text/xml; charset="utf-8"')
        request.add_header(
            "SOAPAction", '"urn:schemas-upnp-org:service:WANIPConnection:1#AddPortMapping"'
        )

        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status == 200

    except Exception as e:
        return False


def delete_port_mapping(device: UPnPDevice, external_port: int, protocol: str = "TCP") -> bool:
    """
    通过 UPnP 删除端口映射

    Args:
        device: 路由器设备
        external_port: 外部端口
        protocol: 协议

    Returns:
        是否成功
    """
    # 查找 WANIPConnection 服务
    service = None
    for s in device.services:
        if "WANIPConnection" in s:
            service = s
            break

    if not service:
        return False

    try:
        import urllib.request
        from urllib.parse import urlparse

        parsed = urlparse(device.location)
        control_url = f"http://{parsed.hostname}:{parsed.port or 80}/upnp/control/WANIPConnection"

        soap_body = (
            f'<?xml version="1.0"?>'
            f'<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
            f's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
            f"<s:Body>"
            f'<u:DeletePortMapping xmlns:u="urn:schemas-upnp-org:service:WANIPConnection:1">'
            f"<NewRemoteHost></NewRemoteHost>"
            f"<NewExternalPort>{external_port}</NewExternalPort>"
            f"<NewProtocol>{protocol}</NewProtocol>"
            f"</u:DeletePortMapping>"
            f"</s:Body>"
            f"</s:Envelope>"
        )

        request = urllib.request.Request(control_url, data=soap_body.encode("utf-8"))
        request.add_header("Content-Type", 'text/xml; charset="utf-8"')
        request.add_header(
            "SOAPAction", '"urn:schemas-upnp-org:service:WANIPConnection:1#DeletePortMapping"'
        )

        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status == 200

    except Exception as e:
        return False


# ══════════════════════════════════════════════════════════════════
# 报告格式化
# ══════════════════════════════════════════════════════════════════


def format_scan_result(result: UPnPScanResult) -> str:
    """格式化扫描结果为文本"""
    lines = []

    lines.append("=" * 60)
    lines.append("UPnP 设备扫描结果")
    lines.append(f"时间: {result.timestamp}")
    lines.append(f"扫描耗时: {result.scan_time_ms} ms")
    lines.append(f"发现设备: {result.total} 个")
    lines.append("=" * 60)
    lines.append("")

    # 按类型分组
    by_type = {}
    for device in result.devices:
        category = device.category.value
        if category not in by_type:
            by_type[category] = []
        by_type[category].append(device)

    for category, devices in sorted(by_type.items()):
        lines.append(f"📦 {category.upper()} ({len(devices)} 个):")

        for device in devices:
            name = device.friendly_name or device.ip
            lines.append(f"  • {name}")
            lines.append(f"    IP: {device.ip}:{device.port}")

            if device.manufacturer:
                lines.append(f"    制造商: {device.manufacturer}")
            if device.model_name:
                lines.append(f"    型号: {device.model_name}")
            if device.serial_number:
                lines.append(f"    序列号: {device.serial_number}")

        lines.append("")

    return "\n".join(lines)
