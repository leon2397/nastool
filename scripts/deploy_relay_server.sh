#!/bin/bash
# deploy_relay_server.sh - NASTool Relay Server deployment for Alibaba ECS

set -e

echo "============================================"
echo "  NASTool Relay Server Deployment"
echo "============================================"

# Update system
echo "[1/5] Updating system..."
sudo apt update && sudo apt upgrade -y

# Install dependencies
echo "[2/5] Installing dependencies..."
sudo apt install -y python3 python3-pip git
pip3 install --upgrade pip
pip3 install websockets requests

# Clone NASTool project
echo "[3/5] Cloning NASTool project..."
git clone https://github.com/your-repo/nastool.git /opt/nastool
cd /opt/nastool

# Create relay server script
echo "[4/5] Creating relay server script..."
cat > /opt/nastool/relay_server.py << 'EOF'
#!/usr/bin/env python3
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
EOF

# Make script executable
chmod +x /opt/nastool/relay_server.py

# Create systemd service
echo "[5/5] Creating systemd service..."
sudo cat > /etc/systemd/system/nastool-relay.service << 'EOF'
[Unit]
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
WantedBy=multi-user.target
EOF

# Start and enable service
sudo systemctl daemon-reload
sudo systemctl start nastool-relay
sudo systemctl enable nastool-relay

# Check service status
echo "============================================"
echo "  Relay Server Deployment Complete!"
echo "============================================"
echo ""
echo "Service status:"
sudo systemctl status nastool-relay
echo ""
echo "Relay Server is running on: ws://120.77.249.3:18888"
echo ""
echo "To check logs: sudo journalctl -u nastool-relay"
echo "To restart service: sudo systemctl restart nastool-relay"
echo ""
echo "============================================"
