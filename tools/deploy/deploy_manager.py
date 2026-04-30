#!/usr/bin/env python3
"""NASTool 一键部署系统"""

import os
import sys
import paramiko
import shutil
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class DeployManager:
    def __init__(self):
        from tools.device_manager import DeviceManager
        self.dm = DeviceManager()
        self.project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    def deploy_to_device(self, device_id, modules=None):
        """部署NASTool到指定设备"""
        device = self.dm.get_device(device_id)
        if not device:
            return {'status': 'error', 'message': '设备不存在'}
        
        print(f'🚀 开始部署到设备: {device["name"]} ({device["ip"]})')
        
        # 默认模块列表
        if not modules:
            modules = ['nastool-core', 'nastool-common', 'nastool-adapters', 'nastool-reporters', 'nastool-cli']
        
        # 建立SSH连接
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                device['ip'],
                port=device['port'],
                username=device['username'],
                password=device['password'],
                timeout=30
            )
            sftp = client.open_sftp()
            
            print('✅ SSH连接成功')
            
            # 创建远程目录
            remote_dir = '/root/nastool'
            self._execute_command(client, f'mkdir -p {remote_dir}/bin')
            print(f'📂 创建目录: {remote_dir}')
            
            # 上传模块
            for module in modules:
                local_path = os.path.join(self.project_root, module)
                remote_path = os.path.join(remote_dir, 'bin', module)
                
                if os.path.exists(local_path):
                    self._upload_directory(sftp, local_path, remote_path)
                    print(f'📦 上传模块: {module}')
                else:
                    print(f'⚠️ 跳过不存在的模块: {module}')
            
            # 创建启动脚本
            self._create_startup_script(client, remote_dir)
            print('📝 创建启动脚本')
            
            # 创建卸载脚本
            self._create_uninstall_script(client, remote_dir)
            print('📝 创建卸载脚本')
            
            # 安装依赖
            self._install_dependencies(client, remote_dir)
            print('📦 安装依赖')
            
            sftp.close()
            client.close()
            
            # 更新设备状态
            self.dm.update_device(device_id, status='deployed', notes='NASTool已部署')
            
            return {
                'status': 'success',
                'message': '部署成功',
                'device_id': device_id,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def deploy_batch(self, device_ids, modules=None):
        """批量部署到多个设备"""
        results = []
        for device_id in device_ids:
            result = self.deploy_to_device(device_id, modules)
            results.append(result)
        return results
    
    def uninstall_from_device(self, device_id):
        """从设备卸载NASTool"""
        device = self.dm.get_device(device_id)
        if not device:
            return {'status': 'error', 'message': '设备不存在'}
        
        print(f'🗑️ 开始卸载设备: {device["name"]} ({device["ip"]})')
        
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                device['ip'],
                port=device['port'],
                username=device['username'],
                password=device['password'],
                timeout=30
            )
            
            # 执行卸载脚本或直接删除目录
            self._execute_command(client, 'rm -rf /root/nastool')
            print('✅ 删除 /root/nastool 目录')
            
            client.close()
            
            # 更新设备状态
            self.dm.update_device(device_id, status='available', notes='NASTool已卸载')
            
            return {
                'status': 'success',
                'message': '卸载成功',
                'device_id': device_id
            }
            
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def check_device_environment(self, device_id):
        """检查设备环境"""
        device = self.dm.get_device(device_id)
        if not device:
            return None
        
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                device['ip'],
                port=device['port'],
                username=device['username'],
                password=device['password'],
                timeout=30
            )
            
            env_info = {}
            
            # 检查Python版本
            result = self._execute_command(client, 'python3 --version 2>&1 || python --version 2>&1')
            env_info['python_version'] = result.strip()
            
            # 检查pip
            result = self._execute_command(client, 'pip3 --version 2>&1 || pip --version 2>&1')
            env_info['pip_version'] = result.strip()
            
            # 检查系统信息
            result = self._execute_command(client, 'cat /etc/os-release | grep PRETTY_NAME')
            env_info['os_version'] = result.strip().replace('PRETTY_NAME=', '').strip('"')
            
            # 检查CPU
            result = self._execute_command(client, 'cat /proc/cpuinfo | grep "model name" | head -1')
            env_info['cpu'] = result.strip().replace('model name\t: ', '')
            
            # 检查内存
            result = self._execute_command(client, 'free -h | grep Mem')
            env_info['memory'] = result.strip()
            
            # 检查磁盘空间
            result = self._execute_command(client, 'df -h / | grep /')
            env_info['disk'] = result.strip()
            
            client.close()
            
            return env_info
            
        except Exception as e:
            return {'error': str(e)}
    
    def _execute_command(self, client, command):
        """执行命令并返回输出"""
        stdin, stdout, stderr = client.exec_command(command)
        return stdout.read().decode('utf-8', errors='ignore')
    
    def _upload_directory(self, sftp, local_dir, remote_dir):
        """上传目录"""
        try:
            sftp.stat(remote_dir)
        except FileNotFoundError:
            sftp.mkdir(remote_dir)
        
        for item in os.listdir(local_dir):
            local_path = os.path.join(local_dir, item)
            remote_path = os.path.join(remote_dir, item)
            
            if os.path.isfile(local_path):
                sftp.put(local_path, remote_path)
            elif os.path.isdir(local_path):
                self._upload_directory(sftp, local_path, remote_path)
    
    def _create_startup_script(self, client, remote_dir):
        """创建启动脚本"""
        script = '''#!/bin/bash
cd /root/nastool
export PYTHONPATH="/root/nastool/bin"
python3 -c "from nastool_core.quick_diagnose import QuickDiagnose; d = QuickDiagnose('quick'); d.run()"
'''
        with client.open_sftp().file(f'{remote_dir}/run.sh', 'w') as f:
            f.write(script)
        self._execute_command(client, f'chmod +x {remote_dir}/run.sh')
    
    def _create_uninstall_script(self, client, remote_dir):
        """创建卸载脚本"""
        script = '''#!/bin/bash
echo "正在卸载NASTool..."
rm -rf /root/nastool
echo "卸载完成!"
'''
        with client.open_sftp().file(f'{remote_dir}/uninstall.sh', 'w') as f:
            f.write(script)
        self._execute_command(client, f'chmod +x {remote_dir}/uninstall.sh')
    
    def _install_dependencies(self, client, remote_dir):
        """安装依赖"""
        requirements_path = os.path.join(self.project_root, 'requirements-full.txt')
        if os.path.exists(requirements_path):
            with open(requirements_path, 'r') as f:
                requirements = f.read()
            
            with client.open_sftp().file(f'{remote_dir}/requirements.txt', 'w') as f:
                f.write(requirements)
            
            self._execute_command(client, f'cd {remote_dir} && pip3 install -r requirements.txt -q')

def main():
    """命令行接口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='NASTool 部署管理器')
    subparsers = parser.add_subparsers(dest='command')
    
    # 部署到单个设备
    deploy_parser = subparsers.add_parser('deploy', help='部署到设备')
    deploy_parser.add_argument('device_id', help='设备ID')
    
    # 批量部署
    batch_parser = subparsers.add_parser('batch', help='批量部署')
    batch_parser.add_argument('device_ids', nargs='+', help='设备ID列表')
    
    # 卸载
    uninstall_parser = subparsers.add_parser('uninstall', help='从设备卸载')
    uninstall_parser.add_argument('device_id', help='设备ID')
    
    # 检查环境
    check_parser = subparsers.add_parser('check', help='检查设备环境')
    check_parser.add_argument('device_id', help='设备ID')
    
    args = parser.parse_args()
    
    dm = DeployManager()
    
    if args.command == 'deploy':
        result = dm.deploy_to_device(args.device_id)
        print(f"\n{'✅' if result['status'] == 'success' else '❌'} {result['message']}")
    
    elif args.command == 'batch':
        results = dm.deploy_batch(args.device_ids)
        print('\n批量部署结果:')
        for result in results:
            status = '✅' if result['status'] == 'success' else '❌'
            print(f"  {status} {result.get('device_id', '')}: {result['message']}")
    
    elif args.command == 'uninstall':
        result = dm.uninstall_from_device(args.device_id)
        print(f"\n{'✅' if result['status'] == 'success' else '❌'} {result['message']}")
    
    elif args.command == 'check':
        env = dm.check_device_environment(args.device_id)
        if env:
            print('\n设备环境信息:')
            for key, value in env.items():
                print(f'  {key}: {value}')
        else:
            print('❌ 无法获取设备环境信息')

if __name__ == '__main__':
    main()
