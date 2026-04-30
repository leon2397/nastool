#!/usr/bin/env python3
"""NASTool 设备管理系统"""

import json
import os
import socket
import paramiko
from datetime import datetime

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'devices.json')

class DeviceManager:
    def __init__(self):
        self.load_devices()
    
    def load_devices(self):
        """加载设备配置"""
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        else:
            self.config = {'version': '1.0', 'devices': [], 'groups': []}
    
    def save_devices(self):
        """保存设备配置"""
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
    
    def list_devices(self, group=None):
        """列出所有设备"""
        devices = self.config['devices']
        
        if group:
            group_info = next((g for g in self.config['groups'] if g['name'] == group), None)
            if group_info:
                devices = [d for d in devices if d['id'] in group_info['devices']]
        
        return devices
    
    def get_device(self, device_id):
        """获取设备信息"""
        return next((d for d in self.config['devices'] if d['id'] == device_id), None)
    
    def add_device(self, name, ip, port=22, username=None, password=None, device_type='generic', notes=''):
        """添加新设备"""
        device_id = f"dev-{len(self.config['devices']):03d}"
        
        device = {
            'id': device_id,
            'name': name,
            'ip': ip,
            'port': port,
            'username': username,
            'password': password,
            'type': device_type,
            'status': 'unknown',
            'last_test': None,
            'notes': notes
        }
        
        self.config['devices'].append(device)
        self.save_devices()
        return device_id
    
    def update_device(self, device_id, **kwargs):
        """更新设备信息"""
        device = self.get_device(device_id)
        if device:
            device.update(kwargs)
            self.save_devices()
            return True
        return False
    
    def remove_device(self, device_id):
        """移除设备"""
        device = self.get_device(device_id)
        if device:
            self.config['devices'].remove(device)
            self.save_devices()
            return True
        return False
    
    def check_status(self, device_id):
        """检查设备状态"""
        device = self.get_device(device_id)
        if not device:
            return None
        
        ip = device['ip']
        port = device['port']
        
        # 检查端口是否开放
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((ip, port))
        sock.close()
        
        if result != 0:
            status = 'offline'
        else:
            # 尝试SSH连接
            if device['username'] and device['password']:
                try:
                    client = paramiko.SSHClient()
                    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    client.connect(
                        ip, 
                        port=port,
                        username=device['username'],
                        password=device['password'],
                        timeout=5
                    )
                    client.close()
                    status = 'online'
                except Exception:
                    status = 'error'
            else:
                status = 'reachable'
        
        # 更新状态
        self.update_device(device_id, status=status, last_test=datetime.now().isoformat())
        return status
    
    def scan_network(self, subnet='192.168.1.', start=1, end=254):
        """扫描局域网设备"""
        results = []
        
        for i in range(start, min(end + 1, 255)):
            ip = f"{subnet}{i}"
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.1)
            result = sock.connect_ex((ip, 22))
            sock.close()
            
            if result == 0:
                results.append({'ip': ip, 'port': 22, 'status': 'open'})
            else:
                # 尝试ping
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.1)
                result = sock.connect_ex((ip, 80))
                sock.close()
                if result == 0:
                    results.append({'ip': ip, 'port': 80, 'status': 'reachable'})
        
        return results

def main():
    """命令行接口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='NASTool 设备管理')
    subparsers = parser.add_subparsers(dest='command')
    
    # 列出设备
    subparsers.add_parser('list', help='列出所有设备')
    
    # 添加设备
    add_parser = subparsers.add_parser('add', help='添加设备')
    add_parser.add_argument('name', help='设备名称')
    add_parser.add_argument('ip', help='IP地址')
    add_parser.add_argument('-p', '--port', type=int, default=22, help='端口')
    add_parser.add_argument('-u', '--username', help='用户名')
    add_parser.add_argument('-pw', '--password', help='密码')
    add_parser.add_argument('-t', '--type', default='generic', help='设备类型')
    add_parser.add_argument('-n', '--notes', default='', help='备注')
    
    # 更新设备
    update_parser = subparsers.add_parser('update', help='更新设备')
    update_parser.add_argument('device_id', help='设备ID')
    update_parser.add_argument('-n', '--name', help='设备名称')
    update_parser.add_argument('-i', '--ip', help='IP地址')
    update_parser.add_argument('-p', '--port', type=int, help='端口')
    update_parser.add_argument('-u', '--username', help='用户名')
    update_parser.add_argument('-pw', '--password', help='密码')
    update_parser.add_argument('-t', '--type', help='设备类型')
    update_parser.add_argument('-nt', '--notes', help='备注')
    
    # 删除设备
    remove_parser = subparsers.add_parser('remove', help='删除设备')
    remove_parser.add_argument('device_id', help='设备ID')
    
    # 检查状态
    status_parser = subparsers.add_parser('status', help='检查设备状态')
    status_parser.add_argument('device_id', nargs='?', help='设备ID，不指定则检查所有')
    
    # 扫描网络
    scan_parser = subparsers.add_parser('scan', help='扫描局域网')
    scan_parser.add_argument('--subnet', default='192.168.1.', help='子网')
    scan_parser.add_argument('--start', type=int, default=1, help='起始IP')
    scan_parser.add_argument('--end', type=int, default=254, help='结束IP')
    
    args = parser.parse_args()
    
    dm = DeviceManager()
    
    if args.command == 'list':
        devices = dm.list_devices()
        print('='*60)
        print('📋 设备列表')
        print('='*60)
        for device in devices:
            status_color = {'online': '✅', 'offline': '❌', 'error': '⚠️', 'reachable': '🔵', 'unknown': '⚪'}
            print(f"{status_color.get(device['status'], '⚪')} {device['id']:10} {device['name']:20} {device['ip']:15} {device['type']:10}")
        print('='*60)
    
    elif args.command == 'add':
        device_id = dm.add_device(
            args.name, args.ip, args.port, 
            args.username, args.password, 
            args.type, args.notes
        )
        print(f'✅ 设备添加成功: {device_id}')
    
    elif args.command == 'update':
        kwargs = {}
        if args.name: kwargs['name'] = args.name
        if args.ip: kwargs['ip'] = args.ip
        if args.port: kwargs['port'] = args.port
        if args.username: kwargs['username'] = args.username
        if args.password: kwargs['password'] = args.password
        if args.type: kwargs['type'] = args.type
        if args.notes: kwargs['notes'] = args.notes
        
        if dm.update_device(args.device_id, **kwargs):
            print(f'✅ 设备 {args.device_id} 更新成功')
        else:
            print(f'❌ 设备 {args.device_id} 不存在')
    
    elif args.command == 'remove':
        if dm.remove_device(args.device_id):
            print(f'✅ 设备 {args.device_id} 删除成功')
        else:
            print(f'❌ 设备 {args.device_id} 不存在')
    
    elif args.command == 'status':
        if args.device_id:
            status = dm.check_status(args.device_id)
            print(f'{args.device_id}: {status}')
        else:
            print('='*60)
            print('🔍 检查所有设备状态')
            print('='*60)
            for device in dm.list_devices():
                status = dm.check_status(device['id'])
                status_color = {'online': '✅', 'offline': '❌', 'error': '⚠️', 'reachable': '🔵'}
                print(f"{status_color.get(status, '⚪')} {device['id']:10} {device['name']:20} {device['ip']:15} -> {status}")
            print('='*60)
    
    elif args.command == 'scan':
        print(f'🔍 扫描子网 {args.subnet}...')
        devices = dm.scan_network(args.subnet, args.start, args.end)
        print('='*60)
        print('📡 发现的设备')
        print('='*60)
        for device in devices:
            print(f"🔵 {device['ip']}:{device['port']}")
        print('='*60)
        print(f'共发现 {len(devices)} 个设备')

if __name__ == '__main__':
    main()
