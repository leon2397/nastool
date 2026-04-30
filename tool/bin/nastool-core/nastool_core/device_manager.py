"""
NASTool Device Management Module

Provides device registration, grouping, tagging, and status caching.

Usage:
    from nastool_core.device_manager import DeviceManager, DeviceGroup

    dm = DeviceManager()
    dm.register_device("rk3588-01", "192.168.1.100", group="prod")
    devices = dm.list_devices(group="prod")
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict


@dataclass
class Device:
    """Device entity"""
    id: str
    host: str
    name: Optional[str] = None
    group: Optional[str] = None
    tags: List[str] = None
    device_type: Optional[str] = None  # rk3588, rk3568, jetson, nas, etc.
    last_seen: Optional[str] = None
    status: str = "unknown"  # online, offline, unknown
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class DeviceGroup:
    """Device group entity"""
    name: str
    description: Optional[str] = None
    device_ids: List[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.device_ids is None:
            self.device_ids = []
        if self.metadata is None:
            self.metadata = {}


class DeviceManager:
    """
    Device management with SQLite backend.

    Features:
    - Device registration and removal
    - Grouping by type/location/project
    - Tagging system
    - Status caching
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize DeviceManager.

        Args:
            db_path: SQLite database path. Default: ~/.nastool/devices.db
        """
        if db_path is None:
            db_path = str(Path.home() / ".nastool" / "devices.db")

        self.db_path = db_path
        self._ensure_db()

    def _ensure_db(self):
        """Ensure database and tables exist"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS devices (
                    id TEXT PRIMARY KEY,
                    host TEXT NOT NULL,
                    name TEXT,
                    group_name TEXT,
                    tags TEXT,  -- JSON array
                    device_type TEXT,
                    last_seen TEXT,
                    status TEXT DEFAULT 'unknown',
                    metadata TEXT,  -- JSON object
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS device_groups (
                    name TEXT PRIMARY KEY,
                    description TEXT,
                    device_ids TEXT,  -- JSON array
                    metadata TEXT,  -- JSON object
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_devices_group ON devices(group_name);
                CREATE INDEX IF NOT EXISTS idx_devices_type ON devices(device_type);
                CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status);
            """)

    # ==================== Device Operations ====================

    def register_device(
        self,
        device_id: str,
        host: str,
        name: Optional[str] = None,
        group: Optional[str] = None,
        tags: Optional[List[str]] = None,
        device_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Device:
        """
        Register a new device or update existing one.

        Args:
            device_id: Unique device identifier
            host: Device host (IP or hostname)
            name: Human-readable name
            group: Group name
            tags: List of tags
            device_type: Device type (rk3588, rk3568, jetson, nas, etc.)
            metadata: Additional metadata

        Returns:
            Device object
        """
        now = datetime.now().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO devices (id, host, name, group_name, tags, device_type, metadata, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    host = excluded.host,
                    name = excluded.name,
                    group_name = excluded.group_name,
                    tags = excluded.tags,
                    device_type = excluded.device_type,
                    metadata = excluded.metadata,
                    updated_at = excluded.updated_at
            """, (
                device_id,
                host,
                name,
                group,
                json.dumps(tags or []),
                device_type,
                json.dumps(metadata or {}),
                now
            ))

        return self.get_device(device_id)

    def get_device(self, device_id: str) -> Optional[Device]:
        """Get device by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM devices WHERE id = ?", (device_id,)
            ).fetchone()

            if row is None:
                return None

            return Device(
                id=row["id"],
                host=row["host"],
                name=row["name"],
                group=row["group_name"],
                tags=json.loads(row["tags"] or "[]"),
                device_type=row["device_type"],
                last_seen=row["last_seen"],
                status=row["status"],
                metadata=json.loads(row["metadata"] or "{}")
            )

    def list_devices(
        self,
        group: Optional[str] = None,
        device_type: Optional[str] = None,
        status: Optional[str] = None,
        tag: Optional[str] = None
    ) -> List[Device]:
        """
        List devices with optional filters.

        Args:
            group: Filter by group
            device_type: Filter by device type
            status: Filter by status
            tag: Filter by tag

        Returns:
            List of Device objects
        """
        query = "SELECT * FROM devices WHERE 1=1"
        params = []

        if group:
            query += " AND group_name = ?"
            params.append(group)

        if device_type:
            query += " AND device_type = ?"
            params.append(device_type)

        if status:
            query += " AND status = ?"
            params.append(status)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()

        devices = []
        for row in rows:
            device = Device(
                id=row["id"],
                host=row["host"],
                name=row["name"],
                group=row["group_name"],
                tags=json.loads(row["tags"] or "[]"),
                device_type=row["device_type"],
                last_seen=row["last_seen"],
                status=row["status"],
                metadata=json.loads(row["metadata"] or "{}")
            )

            # Filter by tag (post-filter since tags are JSON)
            if tag and tag not in device.tags:
                continue

            devices.append(device)

        return devices

    def remove_device(self, device_id: str) -> bool:
        """Remove device by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM devices WHERE id = ?", (device_id,)
            )
            return cursor.rowcount > 0

    def update_device_status(
        self,
        device_id: str,
        status: str,
        last_seen: Optional[str] = None
    ):
        """Update device status"""
        now = datetime.now().isoformat()
        if last_seen is None:
            last_seen = now

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE devices
                SET status = ?, last_seen = ?, updated_at = ?
                WHERE id = ?
            """, (status, last_seen, now, device_id))

    # ==================== Tag Operations ====================

    def add_tag(self, device_id: str, tag: str):
        """Add tag to device"""
        device = self.get_device(device_id)
        if device is None:
            raise ValueError(f"Device not found: {device_id}")

        if tag not in device.tags:
            device.tags.append(tag)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE devices SET tags = ?, updated_at = ? WHERE id = ?",
                    (json.dumps(device.tags), datetime.now().isoformat(), device_id)
                )

    def remove_tag(self, device_id: str, tag: str):
        """Remove tag from device"""
        device = self.get_device(device_id)
        if device is None:
            raise ValueError(f"Device not found: {device_id}")

        if tag in device.tags:
            device.tags.remove(tag)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE devices SET tags = ?, updated_at = ? WHERE id = ?",
                    (json.dumps(device.tags), datetime.now().isoformat(), device_id)
                )

    # ==================== Group Operations ====================

    def create_group(
        self,
        name: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> DeviceGroup:
        """Create a device group"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO device_groups (name, description, metadata)
                VALUES (?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    description = excluded.description,
                    metadata = excluded.metadata
            """, (name, description, json.dumps(metadata or {})))

        return self.get_group(name)

    def get_group(self, name: str) -> Optional[DeviceGroup]:
        """Get group by name"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM device_groups WHERE name = ?", (name,)
            ).fetchone()

            if row is None:
                return None

            # Get device IDs from devices table
            device_ids = [
                r[0] for r in conn.execute(
                    "SELECT id FROM devices WHERE group_name = ?", (name,)
                ).fetchall()
            ]

            return DeviceGroup(
                name=row["name"],
                description=row["description"],
                device_ids=device_ids,
                metadata=json.loads(row["metadata"] or "{}")
            )

    def list_groups(self) -> List[DeviceGroup]:
        """List all groups"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM device_groups").fetchall()

        groups = []
        for row in rows:
            device_ids = [
                r[0] for r in sqlite3.connect(self.db_path).execute(
                    "SELECT id FROM devices WHERE group_name = ?", (row["name"],)
                ).fetchall()
            ]
            groups.append(DeviceGroup(
                name=row["name"],
                description=row["description"],
                device_ids=device_ids,
                metadata=json.loads(row["metadata"] or "{}")
            ))

        return groups

    def delete_group(self, name: str) -> bool:
        """Delete group (devices remain, just ungrouped)"""
        with sqlite3.connect(self.db_path) as conn:
            # Ungroup devices
            conn.execute(
                "UPDATE devices SET group_name = NULL WHERE group_name = ?",
                (name,)
            )
            # Delete group
            cursor = conn.execute(
                "DELETE FROM device_groups WHERE name = ?", (name,)
            )
            return cursor.rowcount > 0

    # ==================== Utility ====================

    def get_stats(self) -> Dict[str, Any]:
        """Get device statistics"""
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM devices").fetchone()[0]
            online = conn.execute(
                "SELECT COUNT(*) FROM devices WHERE status = 'online'"
            ).fetchone()[0]
            offline = conn.execute(
                "SELECT COUNT(*) FROM devices WHERE status = 'offline'"
            ).fetchone()[0]
            groups = conn.execute("SELECT COUNT(*) FROM device_groups").fetchone()[0]

        return {
            "total": total,
            "online": online,
            "offline": offline,
            "unknown": total - online - offline,
            "groups": groups
        }
