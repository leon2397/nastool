#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deploy NASTool Relay Server to Alibaba ECS
"""

import paramiko
import time

# ECS connection details
ECS_IP = "120.77.249.3"
ECS_USER = "root"
ECS_PASSWORD = "Zy23973751"

# Relay server script content
RELAY_SERVER_SCRIPT = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NASTool Relay Server

This server acts as a relay between NASTool CLI and remote devices.
It provides a WebSocket interface for device agents to connect to.
"""

import asyncio
import websockets
import json
import logging
import argparse
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('nastool.relay')

class RelayServer:
    """Relay Server for NASTool"""
    
    def __init__(self, host='0.0.0.0', port=18888, api_key=None):
        self.host = host
        self.port = port
        self.api_key = api_key
        self.connected_devices = {}
        self.device_queues = {}
    
    async def handle_connection(self, websocket, path):
        """Handle incoming WebSocket connections"""
        device_id = None
        
        try:
            # Wait for device registration
            while True:
                message = await websocket.recv()
                data = json.loads(message)
                
                if data.get('type') == 'register':
                    device_id = data.get('device_id')
                    device_name = data.get('device_name', 'Unknown')
                    device_type = data.get('device_type', 'unknown')
                    
                    if device_id:
                        self.connected_devices[device_id] = {
                            'websocket': websocket,
                            'name': device_name,
                            'type': device_type,
                            'connected_at': datetime.now().isoformat(),
                            'last_activity': datetime.now().isoformat()
                        }
                        self.device_queues[device_id] = asyncio.Queue()
                        
                        # Send registration response
                        await websocket.send(json.dumps({
                            'type': 'register_response',
                            'status': 'ok',
                            'message': f'Device {device_id} registered successfully'
                        }))
                        
                        logger.info(f'Device registered: {device_id} ({device_name})')
                        break
        
        except Exception as e:
            logger.error(f'Error during registration: {e}')
            if device_id and device_id in self.connected_devices:
                del self.connected_devices[device_id]
                del self.device_queues[device_id]
            return
        
        # Handle device communication
        try:
            while True:
                # Wait for messages from device
                message = await websocket.recv()
                data = json.loads(message)
                
                # Update last activity
                if device_id in self.connected_devices:
                    self.connected_devices[device_id]['last_activity'] = datetime.now().isoformat()
                
                # Handle different message types
                if data.get('type') == 'ping':
                    # Respond to ping
                    await websocket.send(json.dumps({
                        'type': 'pong',
                        'timestamp': datetime.now().isoformat()
                    }))
                
                elif data.get('type') == 'status':
                    # Broadcast status update
                    logger.info(f'Status update from {device_id}: {data.get("status")}')
                
                elif data.get('type') == 'diagnosis_result':
                    # Store diagnosis result
                    if device_id in self.device_queues:
                        await self.device_queues[device_id].put(data)
                
                else:
                    logger.warning(f'Unknown message type: {data.get("type")}')
        
        except websockets.exceptions.ConnectionClosed:
            logger.info(f'Device disconnected: {device_id}')
        except Exception as e:
            logger.error(f'Error handling device {device_id}: {e}')
        finally:
            # Clean up
            if device_id and device_id in self.connected_devices:
                del self.connected_devices[device_id]
                del self.device_queues[device_id]
                logger.info(f'Device removed: {device_id}')
    
    async def quick_scan(self):
        """Quick scan of connected devices"""
        devices = []
        for device_id, info in self.connected_devices.items():
            devices.append({
                'device_id': device_id,
                'device_name': info['name'],
                'device_type': info['type'],
                'status': 'online',
                'connected_at': info['connected_at'],
                'last_activity': info['last_activity']
            })
        
        return {
            'total': len(devices),
            'online': len(devices),
            'devices': devices
        }
    
    async def run_diagnosis(self, device_id, full_mode=False):
        """Run diagnosis on a specific device"""
        if device_id not in self.connected_devices:
            return {'error': 'Device not found'}
        
        # Send diagnosis request
        websocket = self.connected_devices[device_id]['websocket']
        await websocket.send(json.dumps({
            'type': 'diagnosis_request',
            'full_mode': full_mode
        }))
        
        # Wait for result
        try:
            result = await asyncio.wait_for(
                self.device_queues[device_id].get(),
                timeout=300
            )
            return result.get('result', {})
        except asyncio.TimeoutError:
            return {'error': 'Diagnosis timeout'}
    
    async def start(self):
        """Start the relay server"""
        server = await websockets.serve(
            self.handle_connection,
            self.host,
            self.port
        )
        
        logger.info(f'Relay Server started on ws://{self.host}:{self.port}')
        
        # Keep server running
        await server.wait_closed()

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='NASTool Relay Server'
    )
    
    parser.add_argument('--host', default='0.0.0.0',
                      help='Host to listen on (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=18888,
                      help='Port to listen on (default: 18888)')
    parser.add_argument('--key', help='API key for authentication')
    
    args = parser.parse_args()
    
    server = RelayServer(
        host=args.host,
        port=args.port,
        api_key=args.key
    )
    
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        logger.info('Relay Server stopped')

if __name__ == '__main__':
    main()
'''

def run_ssh_command(ssh_client, command):
    """Run SSH command and return output"""
    stdin, stdout, stderr = ssh_client.exec_command(command)
    output = stdout.read().decode('utf-8')
    error = stderr.read().decode('utf-8')
    return output, error

def main():
    """Main deployment function"""
    print("============================================")
    print("  NASTool Relay Server Deployment")
    print("============================================")
    
    try:
        # Create SSH client
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Connect to ECS
        print("[1/5] Connecting to ECS...")
        ssh_client.connect(
            hostname=ECS_IP,
            username=ECS_USER,
            password=ECS_PASSWORD,
            timeout=30
        )
        print("✓ Connected successfully")
        
        # Update system
        print("[2/5] Updating system...")
        output, error = run_ssh_command(ssh_client, "sudo apt update && sudo apt upgrade -y")
        if error:
            print(f"⚠️  Error during update: {error}")
        else:
            print("✓ System updated")
        
        # Install dependencies
        print("[3/5] Installing dependencies...")
        output, error = run_ssh_command(ssh_client, "sudo apt install -y python3 python3-pip && pip3 install --upgrade pip && pip3 install websockets requests")
        if error:
            print(f"⚠️  Error during dependency installation: {error}")
        else:
            print("✓ Dependencies installed")
        
        # Create relay server directory
        print("[4/5] Creating relay server directory...")
        run_ssh_command(ssh_client, "mkdir -p /opt/nastool")
        
        # Create relay server script
        print("[5/5] Creating relay server script...")
        # Write relay server script using echo
        escaped_script = RELAY_SERVER_SCRIPT.replace('"', '\\"').replace('\n', '\\n')
        command = f'echo "{escaped_script}" > /opt/nastool/relay_server.py && chmod +x /opt/nastool/relay_server.py'
        output, error = run_ssh_command(ssh_client, command)
        if error:
            print(f"⚠️  Error creating relay server script: {error}")
        else:
            print("✓ Relay server script created")
        
        # Create systemd service
        print("[6/5] Creating systemd service...")
        service_content = '''[Unit]
Description=NASTool Relay Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/nastool
ExecStart=/usr/bin/python3 relay_server.py --host 0.0.0.0 --port 18888
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target'''
        escaped_service = service_content.replace('"', '\\"').replace('\n', '\\n')
        command = f'echo "{escaped_service}" | sudo tee /etc/systemd/system/nastool-relay.service'
        output, error = run_ssh_command(ssh_client, command)
        if error:
            print(f"⚠️  Error creating systemd service: {error}")
        else:
            print("✓ Systemd service created")
        
        # Start and enable service
        print("[7/5] Starting and enabling service...")
        commands = [
            "sudo systemctl daemon-reload",
            "sudo systemctl start nastool-relay",
            "sudo systemctl enable nastool-relay"
        ]
        for cmd in commands:
            output, error = run_ssh_command(ssh_client, cmd)
            if error:
                print(f"⚠️  Error running command {cmd}: {error}")
        print("✓ Service started and enabled")
        
        # Check service status
        print("[8/5] Checking service status...")
        output, error = run_ssh_command(ssh_client, "sudo systemctl status nastool-relay")
        print(output)
        if error:
            print(f"⚠️  Error checking service status: {error}")
        
        # Test connection
        print("[9/5] Testing Relay Server connection...")
        output, error = run_ssh_command(ssh_client, "netstat -tuln | grep 18888")
        if output:
            print("✓ Relay Server is listening on port 18888")
        else:
            print("⚠️  Relay Server is not listening on port 18888")
        
        print("============================================")
        print("  Relay Server Deployment Complete!")
        print("============================================")
        print(f"Relay Server is running on: ws://{ECS_IP}:18888")
        print("To check logs: sudo journalctl -u nastool-relay")
        print("To restart service: sudo systemctl restart nastool-relay")
        print("============================================")
        
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
    finally:
        # Close SSH connection
        if 'ssh_client' in locals() and ssh_client:
            ssh_client.close()

if __name__ == '__main__':
    main()
