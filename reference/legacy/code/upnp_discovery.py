import asyncio
import socket
import xml.etree.ElementTree as ET
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

SSDP_MULTICAST_ADDR = '239.255.255.250'
SSDP_PORT = 1900
SSDP_SEARCH_MSG = (
    'M-SEARCH * HTTP/1.1\r\n'
    'HOST: 239.255.255.250:1900\r\n'
    'MAN: "ssdp:discover"\r\n'
    'MX: 3\r\n'
    'ST: ssdp:all\r\n'
    '\r\n'
)

class UPnPDevice:
    def __init__(self, location: str):
        self.location = location
        self.device_type = None
        self.friendly_name = None
        self.manufacturer = None
        self.model_name = None
        self.udn = None
        self.services = []
    
    def parse_description(self, xml_content: str):
        """解析设备描述XML"""
        try:
            root = ET.fromstring(xml_content)
            
            ns = {
                'upnp': 'urn:schemas-upnp-org:device-1-0',
                'dc': 'http://purl.org/dc/elements/1.1/'
            }
            
            device = root.find('upnp:device', ns)
            
            if device is not None:
                self.friendly_name = device.findtext('upnp:friendlyName', '', ns)
                self.manufacturer = device.findtext('upnp:manufacturer', '', ns)
                self.model_name = device.findtext('upnp:modelName', '', ns)
                self.udn = device.findtext('upnp:UDN', '', ns)
                self.device_type = device.findtext('upnp:deviceType', '', ns)
                
                services = device.findall('upnp:serviceList/upnp:service', ns)
                for service in services:
                    service_type = service.findtext('upnp:serviceType', '', ns)
                    control_url = service.findtext('upnp:controlURL', '', ns)
                    self.services.append({
                        'type': service_type,
                        'control_url': control_url
                    })
        except Exception as e:
            logger.error(f"Failed to parse UPnP device description: {e}")
    
    def to_dict(self):
        return {
            'location': self.location,
            'device_type': self.device_type,
            'friendly_name': self.friendly_name,
            'manufacturer': self.manufacturer,
            'model_name': self.model_name,
            'udn': self.udn,
            'services': self.services
        }

class UPnPDiscovery:
    def __init__(self):
        self.devices: List[UPnPDevice] = []
    
    async def discover(self, timeout: int = 5) -> List[UPnPDevice]:
        """发现局域网中的UPnP设备"""
        self.devices = []
        
        loop = asyncio.get_event_loop()
        discovered_devices = set()
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
            sock.settimeout(timeout)
            
            await loop.run_in_executor(None, sock.sendto, SSDP_MULTICAST_MSG.encode(), (SSDP_MULTICAST_ADDR, SSDP_PORT))
            
            start_time = loop.time()
            while loop.time() - start_time < timeout:
                try:
                    data, addr = await loop.run_in_executor(None, sock.recvfrom, 4096)
                    
                    response = data.decode('utf-8', errors='ignore')
                    
                    if 'LOCATION:' in response:
                        lines = response.split('\r\n')
                        location = None
                        for line in lines:
                            if line.startswith('LOCATION:'):
                                location = line[9:].strip()
                                break
                        
                        if location and location not in discovered_devices:
                            discovered_devices.add(location)
                            device = UPnPDevice(location)
                            
                            await self._fetch_device_description(device)
                            self.devices.append(device)
                            
                except socket.timeout:
                    break
                except Exception as e:
                    logger.debug(f"Error receiving UPnP response: {e}")
            
            sock.close()
        
        except Exception as e:
            logger.error(f"UPnP discovery failed: {e}")
        
        return self.devices
    
    async def _fetch_device_description(self, device: UPnPDevice):
        """获取设备描述"""
        import aiohttp
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(device.location) as response:
                    if response.status == 200:
                        xml_content = await response.text()
                        device.parse_description(xml_content)
        except Exception as e:
            logger.debug(f"Failed to fetch device description from {device.location}: {e}")
    
    def get_devices_by_type(self, device_type: str) -> List[UPnPDevice]:
        """按设备类型筛选"""
        return [d for d in self.devices if device_type.lower() in (d.device_type or '').lower()]
    
    def get_device_by_udn(self, udn: str) -> UPnPDevice:
        """按UDN查找设备"""
        for device in self.devices:
            if device.udn == udn:
                return device
        return None
    
    def list_devices(self) -> List[Dict]:
        """获取所有设备列表"""
        return [d.to_dict() for d in self.devices]