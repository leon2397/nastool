"""
commands/device.py - 设备管理命令

对应原 main.py 中的 device 子命令。
"""

import argparse
from typing import Optional

from nastool_core import DeviceManager
from nastool_common.logger import get_logger

from . import Command, register_command

logger = get_logger(__name__)


@register_command(
    name="device",
    help="Device management",
    aliases=["dev"]
)
class DeviceCommand(Command):
    """设备管理命令"""
    
    def add_arguments(self, parser: argparse.ArgumentParser):
        subparsers = parser.add_subparsers(dest="device_cmd", help="Device commands")
        
        # list
        list_parser = subparsers.add_parser("list", help="List devices")
        list_parser.add_argument("--group", "-g", help="Filter by group")
        list_parser.add_argument("--type", "-t", help="Filter by device type")
        
        # add
        add_parser = subparsers.add_parser("add", help="Add device")
        add_parser.add_argument("host", help="Device host (IP or hostname)")
        add_parser.add_argument("--id", help="Device ID")
        add_parser.add_argument("--name", "-n", help="Device name")
        add_parser.add_argument("--group", "-g", help="Group name")
        add_parser.add_argument("--type", "-t", help="Device type")
        
        # remove
        remove_parser = subparsers.add_parser("remove", help="Remove device")
        remove_parser.add_argument("device_id", help="Device ID")
        
        # tag
        tag_parser = subparsers.add_parser("tag", help="Add tag to device")
        tag_parser.add_argument("device_id", help="Device ID")
        tag_parser.add_argument("--tag", "-t", required=True, help="Tag to add")
    
    def execute(self, args: argparse.Namespace) -> int:
        """执行设备命令"""
        dm = DeviceManager()
        
        cmd = getattr(args, "device_cmd", None)
        
        if cmd == "list":
            return self._cmd_list(dm, args)
        elif cmd == "add":
            return self._cmd_add(dm, args)
        elif cmd == "remove":
            return self._cmd_remove(dm, args)
        elif cmd == "tag":
            return self._cmd_tag(dm, args)
        else:
            print("Usage: nastool device <list|add|remove|tag>")
            return 1
    
    def _cmd_list(self, dm: DeviceManager, args) -> int:
        """列出设备"""
        devices = dm.list_devices(
            group=getattr(args, 'group', None),
            device_type=getattr(args, 'type', None)
        )
        
        if not devices:
            print("No devices found.")
            return 0
        
        print(f"\n  Total: {len(devices)} devices\n")
        print(f"  {'ID':<20} {'Host':<20} {'Type':<10} {'Group':<10} {'Status':<8}")
        print(f"  {'-'*20} {'-'*20} {'-'*10} {'-'*10} {'-'*8}")
        
        for d in devices:
            status_icon = "[ON]" if d.status == "online" else "[OFF]" if d.status == "offline" else "[?]"
            print(f"  {d.id:<20} {d.host:<20} {(d.device_type or '-'):<10} {(d.group or '-'):<10} {status_icon} {d.status}")
        
        print()
        return 0
    
    def _cmd_add(self, dm: DeviceManager, args) -> int:
        """添加设备"""
        device_id = args.id or args.host.replace(".", "-")
        dm.register_device(
            device_id=device_id,
            host=args.host,
            name=getattr(args, 'name', None),
            group=getattr(args, 'group', None),
            device_type=getattr(args, 'type', None)
        )
        print(f"Device registered: {device_id} ({args.host})")
        return 0
    
    def _cmd_remove(self, dm: DeviceManager, args) -> int:
        """移除设备"""
        if dm.remove_device(args.device_id):
            print(f"Device removed: {args.device_id}")
            return 0
        else:
            print(f"Device not found: {args.device_id}")
            return 1
    
    def _cmd_tag(self, dm: DeviceManager, args) -> int:
        """添加标签"""
        dm.add_tag(args.device_id, args.tag)
        print(f"Tag '{args.tag}' added to {args.device_id}")
        return 0
