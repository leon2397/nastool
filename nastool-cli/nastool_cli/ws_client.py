"""
NASTool WebSocket Client Module

Provides real-time communication with Relay Server.

Usage:
    from nastool_cli.ws_client import WebSocketClient, WSMessage

    client = WebSocketClient("ws://localhost:18888/ws/gui")
    client.on_device_update = lambda msg: print(msg)
    client.connect()
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass, asdict
from enum import Enum

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

from nastool_common.logger import get_logger

logger = get_logger(__name__)


# Protocol version (must match relay_server)
PROTOCOL_VERSION = "2.0.0"


class MessageType(Enum):
    """WebSocket message types (v2.0 protocol)"""
    # Agent → Server
    AGENT_REGISTER = "agent:register"
    AGENT_HEARTBEAT = "agent:heartbeat"
    AGENT_STATUS = "agent:status"
    AGENT_COMMAND_RESULT = "agent:command_result"
    AGENT_REPORT = "agent:report"

    # Server → Agent
    SERVER_COMMAND = "server:command"
    SERVER_DEPLOY = "server:deploy"
    SERVER_CONFIG_UPDATE = "server:config_update"
    SERVER_PING = "server:ping"

    # GUI → Server
    GUI_SUBSCRIBE = "gui:subscribe"
    GUI_UNSUBSCRIBE = "gui:unsubscribe"
    GUI_COMMAND = "gui:command"

    # Server → GUI
    GUI_DEVICE_UPDATE = "gui:device_update"
    GUI_COMMAND_PROGRESS = "gui:command_progress"
    GUI_NOTIFICATION = "gui:notification"


@dataclass
class WSMessage:
    """WebSocket message structure"""
    type: str
    id: str
    timestamp: int
    source: str
    protocol_version: str
    payload: Dict[str, Any]
    in_reply_to: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WSMessage":
        return cls(
            type=data["type"],
            id=data["id"],
            timestamp=data["timestamp"],
            source=data["source"],
            protocol_version=data["protocol_version"],
            payload=data.get("payload", {}),
            in_reply_to=data.get("in_reply_to")
        )

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "type": self.type,
            "id": self.id,
            "timestamp": self.timestamp,
            "source": self.source,
            "protocol_version": self.protocol_version,
            "payload": self.payload
        }
        if self.in_reply_to:
            result["in_reply_to"] = self.in_reply_to
        return result


class WebSocketClient:
    """
    WebSocket client for real-time communication with Relay Server.

    Features:
    - Auto-reconnect on disconnect
    - Message type routing
    - Subscription management
    - Heartbeat handling
    """

    def __init__(
        self,
        url: str,
        api_key: Optional[str] = None,
        reconnect: bool = True,
        reconnect_interval: int = 5
    ):
        """
        Initialize WebSocket client.

        Args:
            url: WebSocket URL (ws://host:port/ws/gui)
            api_key: API key for authentication
            reconnect: Auto-reconnect on disconnect
            reconnect_interval: Reconnect interval in seconds
        """
        if not WEBSOCKETS_AVAILABLE:
            raise ImportError(
                "websockets library not installed. "
                "Install with: pip install websockets"
            )

        self.url = url
        self.api_key = api_key
        self.reconnect = reconnect
        self.reconnect_interval = reconnect_interval

        self._ws = None
        self._running = False
        self._subscribed_devices: set = set()

        # Callbacks
        self.on_device_update: Optional[Callable[[WSMessage], None]] = None
        self.on_command_progress: Optional[Callable[[WSMessage], None]] = None
        self.on_notification: Optional[Callable[[WSMessage], None]] = None
        self.on_connected: Optional[Callable[[], None]] = None
        self.on_disconnected: Optional[Callable[[], None]] = None

    # ==================== Connection ====================

    async def connect(self) -> bool:
        """
        Connect to WebSocket server.

        Returns:
            True if connected successfully
        """
        try:
            # Build URL with API key
            url = self.url
            if self.api_key:
                separator = "&" if "?" in url else "?"
                url = f"{url}{separator}key={self.api_key}"

            self._ws = await websockets.connect(url)
            self._running = True

            if self.on_connected:
                self.on_connected()

            logger.info(f"WebSocket connected: {self.url}")
            return True

        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            return False

    async def disconnect(self):
        """Disconnect from WebSocket server"""
        self._running = False
        if self._ws:
            await self._ws.close()
            self._ws = None

        if self.on_disconnected:
            self.on_disconnected()

        logger.info("WebSocket disconnected")

    async def listen(self):
        """
        Listen for messages (blocking).

        Handles:
        - Message routing by type
        - Heartbeat (ping/pong)
        - Auto-reconnect
        """
        while self._running:
            try:
                if self._ws is None:
                    if self.reconnect:
                        await asyncio.sleep(self.reconnect_interval)
                        await self.connect()
                        continue
                    else:
                        break

                # Receive message
                raw = await self._ws.recv()
                data = json.loads(raw)
                msg = WSMessage.from_dict(data)

                # Route by message type
                await self._handle_message(msg)

            except websockets.ConnectionClosed:
                logger.warning("WebSocket connection closed")
                self._ws = None

                if self.on_disconnected:
                    self.on_disconnected()

                if not self.reconnect:
                    break

            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                await asyncio.sleep(1)

    async def _handle_message(self, msg: WSMessage):
        """Handle incoming message by type"""
        if msg.type == MessageType.SERVER_PING.value:
            # Respond to ping
            await self._send_pong(msg)

        elif msg.type == MessageType.GUI_DEVICE_UPDATE.value:
            if self.on_device_update:
                self.on_device_update(msg)

        elif msg.type == MessageType.GUI_COMMAND_PROGRESS.value:
            if self.on_command_progress:
                self.on_command_progress(msg)

        elif msg.type == MessageType.GUI_NOTIFICATION.value:
            if self.on_notification:
                self.on_notification(msg)

        else:
            logger.debug(f"Unhandled message type: {msg.type}")

    # ==================== Sending ====================

    async def send(self, msg: WSMessage):
        """Send a message"""
        if self._ws is None:
            raise ConnectionError("WebSocket not connected")

        await self._ws.send(json.dumps(msg.to_dict()))

    async def _send_pong(self, ping_msg: WSMessage):
        """Send pong response to ping"""
        pong = WSMessage(
            type="pong",
            id=self._generate_id(),
            timestamp=int(time.time() * 1000),
            source="gui",
            protocol_version=PROTOCOL_VERSION,
            payload={},
            in_reply_to=ping_msg.id
        )
        await self.send(pong)

    # ==================== Subscription ====================

    async def subscribe(self, device_ids: List[str]):
        """
        Subscribe to device updates.

        Args:
            device_ids: List of device IDs to subscribe
        """
        msg = WSMessage(
            type=MessageType.GUI_SUBSCRIBE.value,
            id=self._generate_id(),
            timestamp=int(time.time() * 1000),
            source="gui",
            protocol_version=PROTOCOL_VERSION,
            payload={"device_ids": device_ids}
        )
        await self.send(msg)

        self._subscribed_devices.update(device_ids)
        logger.info(f"Subscribed to devices: {device_ids}")

    async def unsubscribe(self, device_ids: List[str]):
        """
        Unsubscribe from device updates.

        Args:
            device_ids: List of device IDs to unsubscribe
        """
        msg = WSMessage(
            type=MessageType.GUI_UNSUBSCRIBE.value,
            id=self._generate_id(),
            timestamp=int(time.time() * 1000),
            source="gui",
            protocol_version=PROTOCOL_VERSION,
            payload={"device_ids": device_ids}
        )
        await self.send(msg)

        self._subscribed_devices.difference_update(device_ids)
        logger.info(f"Unsubscribed from devices: {device_ids}")

    # ==================== Commands ====================

    async def send_command(
        self,
        device_id: str,
        cmd: str,
        timeout_ms: int = 30000
    ) -> str:
        """
        Send command to device.

        Args:
            device_id: Target device ID
            cmd: Command to execute
            timeout_ms: Command timeout

        Returns:
            Command ID
        """
        command_id = self._generate_id()

        msg = WSMessage(
            type=MessageType.GUI_COMMAND.value,
            id=self._generate_id(),
            timestamp=int(time.time() * 1000),
            source="gui",
            protocol_version=PROTOCOL_VERSION,
            payload={
                "device_id": device_id,
                "command_id": command_id,
                "cmd": cmd,
                "timeout_ms": timeout_ms
            }
        )
        await self.send(msg)

        logger.info(f"Command sent to {device_id}: {cmd}")
        return command_id

    # ==================== Utilities ====================

    def _generate_id(self) -> str:
        """Generate unique message ID"""
        import random
        return f"{int(time.time() * 1000):x}_{random.randint(0, 0xFFFFFF):06x}"


class WebSocketMonitor:
    """
    High-level WebSocket monitor for device status.

    Features:
    - Device status tracking
    - Alert on status change
    - Progress tracking
    """

    def __init__(
        self,
        relay_url: str,
        api_key: Optional[str] = None
    ):
        """
        Initialize WebSocket monitor.

        Args:
            relay_url: Relay Server URL
            api_key: API key
        """
        self.relay_url = relay_url
        self.api_key = api_key

        # Build WebSocket URL
        if relay_url.startswith("http://"):
            ws_url = relay_url.replace("http://", "ws://")
        elif relay_url.startswith("https://"):
            ws_url = relay_url.replace("https://", "wss://")
        else:
            ws_url = relay_url

        # Ensure /ws/gui path
        if not ws_url.endswith("/ws/gui"):
            ws_url = ws_url.rstrip("/") + "/ws/gui"

        self.client = WebSocketClient(ws_url, api_key)

        # State
        self.device_status: Dict[str, Dict[str, Any]] = {}
        self.command_progress: Dict[str, Dict[str, Any]] = {}

        # Set up callbacks
        self.client.on_device_update = self._on_device_update
        self.client.on_command_progress = self._on_command_progress
        self.client.on_notification = self._on_notification

    def _on_device_update(self, msg: WSMessage):
        """Handle device update"""
        payload = msg.payload
        device_id = payload.get("device_id")
        if device_id:
            self.device_status[device_id] = payload
            logger.info(f"Device update: {device_id} - {payload.get('status')}")

    def _on_command_progress(self, msg: WSMessage):
        """Handle command progress"""
        payload = msg.payload
        command_id = payload.get("command_id")
        if command_id:
            self.command_progress[command_id] = payload
            logger.debug(f"Command progress: {command_id} - {payload.get('progress')}%")

    def _on_notification(self, msg: WSMessage):
        """Handle notification"""
        payload = msg.payload
        level = payload.get("level", "info")
        message = payload.get("message", "")
        logger.info(f"Notification [{level}]: {message}")

    async def start(self, device_ids: Optional[List[str]] = None):
        """
        Start monitoring.

        Args:
            device_ids: Device IDs to monitor (optional)
        """
        connected = await self.client.connect()
        if not connected:
            raise ConnectionError(f"Failed to connect to {self.relay_url}")

        if device_ids:
            await self.client.subscribe(device_ids)

        await self.client.listen()

    async def stop(self):
        """Stop monitoring"""
        await self.client.disconnect()

    def get_device_status(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get device status"""
        return self.device_status.get(device_id)

    def get_command_progress(self, command_id: str) -> Optional[Dict[str, Any]]:
        """Get command progress"""
        return self.command_progress.get(command_id)


# ==================== Sync Wrapper ====================

def run_monitor(
    relay_url: str,
    device_ids: Optional[List[str]] = None,
    api_key: Optional[str] = None,
    on_update: Optional[Callable[[Dict[str, Any]], None]] = None
):
    """
    Run WebSocket monitor (blocking, sync wrapper).

    Args:
        relay_url: Relay Server URL
        device_ids: Device IDs to monitor
        api_key: API key
        on_update: Callback for device updates
    """
    monitor = WebSocketMonitor(relay_url, api_key)

    if on_update:
        original_callback = monitor._on_device_update
        def wrapped_callback(msg: WSMessage):
            original_callback(msg)
            on_update(msg.payload)
        monitor.client.on_device_update = wrapped_callback

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(monitor.start(device_ids))
    except KeyboardInterrupt:
        loop.run_until_complete(monitor.stop())
    finally:
        loop.close()
