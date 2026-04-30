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
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Iterator
from dataclasses import dataclass, asdict


@dataclass
class Device:
    """Device entity"""
    id: str
    host: str
    name: Optional[str] = None
    group: Optional[str] = None
    tags: List[str] = None
    device_type: Optional[str] = None
    last_seen: Optional[str] = None
    status: str = "unknown"
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Device":
        """Create from dictionary"""
        return cls(**data)


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

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class DeviceManager:
    """
    Device management with SQLite backend.

    Features:
    - Device registration and removal
    - Grouping by type/location/project
    - Tagging system
    - Status caching
    - Connection pooling for better performance
    - Batch operations
    """

    _local = threading.local()

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

    def _get_connection(self) -> sqlite3.Connection:
        """获取线程本地的数据库连接"""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection

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
                    tags TEXT,
                    device_type TEXT,
                    last_seen TEXT,
                    status TEXT DEFAULT 'unknown',
                    metadata TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS device_groups (
                    name TEXT PRIMARY KEY,
                    description TEXT,
                    metadata TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_devices_group ON devices(group_name);
                CREATE INDEX IF NOT EXISTS idx_devices_type ON devices(device_type);
                CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status);
            """)

    def _row_to_device(self, row: sqlite3.Row) -> Device:
        """Convert row to Device object"""
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

    def _row_to_group(self, row: sqlite3.Row, device_ids: List[str]) -> DeviceGroup:
        """Convert row to DeviceGroup object"""
        return DeviceGroup(
            name=row["name"],
            description=row["description"],
            device_ids=device_ids,
            metadata=json.loads(row["metadata"] or "{}")
        )

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

    def batch_register_devices(self, devices: List[Dict[str, Any]]) -> int:
        """
        Batch register devices.

        Args:
            devices: List of device dictionaries

        Returns:
            Number of devices registered
        """
        now = datetime.now().isoformat()
        count = 0

        with sqlite3.connect(self.db_path) as conn:
            for dev in devices:
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
                    dev.get("id"),
                    dev.get("host"),
                    dev.get("name"),
                    dev.get("group"),
                    json.dumps(dev.get("tags", [])),
                    dev.get("device_type"),
                    json.dumps(dev.get("metadata", {})),
                    now
                ))
                count += 1

        return count

    def get_device(self, device_id: str) -> Optional[Device]:
        """Get device by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM devices WHERE id = ?", (device_id,)
            ).fetchone()

            if row is None:
                return None

            return self._row_to_device(row)

    def list_devices(
        self,
        group: Optional[str] = None,
        device_type: Optional[str] = None,
        status: Optional[str] = None,
        tag: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Device]:
        """
        List devices with optional filters.

        Args:
            group: Filter by group
            device_type: Filter by device type
            status: Filter by status
            tag: Filter by tag
            limit: Maximum number of results
            offset: Number of results to skip

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

        query += " ORDER BY id"

        if limit is not None:
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()

        devices = []
        for row in rows:
            device = self._row_to_device(row)
            if tag and tag not in device.tags:
                continue
            devices.append(device)

        return devices

    def iter_devices(
        self,
        group: Optional[str] = None,
        device_type: Optional[str] = None,
        batch_size: int = 100
    ) -> Iterator[Device]:
        """
        Iterate devices in batches (memory efficient).

        Args:
            group: Filter by group
            device_type: Filter by device type
            batch_size: Number of devices per batch

        Yields:
            Device objects
        """
        offset = 0
        while True:
            devices = self.list_devices(
                group=group,
                device_type=device_type,
                limit=batch_size,
                offset=offset
            )
            if not devices:
                break
            for device in devices:
                yield device
            offset += batch_size

    def batch_update_status(self, updates: Dict[str, str]) -> int:
        """
        Batch update device status.

        Args:
            updates: Dictionary of device_id -> status

        Returns:
            Number of devices updated
        """
        now = datetime.now().isoformat()
        count = 0

        with sqlite3.connect(self.db_path) as conn:
            for device_id, status in updates.items():
                conn.execute("""
                    UPDATE devices
                    SET status = ?, last_seen = ?, updated_at = ?
                    WHERE id = ?
                """, (status, now, now, device_id))
                count += 1

        return count

    def remove_device(self, device_id: str) -> bool:
        """Remove device by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM devices WHERE id = ?", (device_id,)
            )
            return cursor.rowcount > 0

    def batch_remove_devices(self, device_ids: List[str]) -> int:
        """
        Batch remove devices.

        Args:
            device_ids: List of device IDs

        Returns:
            Number of devices removed
        """
        count = 0
        with sqlite3.connect(self.db_path) as conn:
            for device_id in device_ids:
                cursor = conn.execute(
                    "DELETE FROM devices WHERE id = ?", (device_id,)
                )
                count += cursor.rowcount
        return count

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

            device_ids = [
                r[0] for r in conn.execute(
                    "SELECT id FROM devices WHERE group_name = ?", (name,)
                ).fetchall()
            ]

            return self._row_to_group(row, device_ids)

    def list_groups(self) -> List[DeviceGroup]:
        """List all groups"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM device_groups").fetchall()

            groups = []
            for row in rows:
                device_ids = [
                    r[0] for r in conn.execute(
                        "SELECT id FROM devices WHERE group_name = ?", (row["name"],)
                    ).fetchall()
                ]
                groups.append(self._row_to_group(row, device_ids))

        return groups

    def delete_group(self, name: str) -> bool:
        """Delete group (devices remain, just ungrouped)"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE devices SET group_name = NULL WHERE group_name = ?",
                (name,)
            )
            cursor = conn.execute(
                "DELETE FROM device_groups WHERE name = ?", (name,)
            )
            return cursor.rowcount > 0

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

    def search_devices(self, keyword: str) -> List[Device]:
        """
        Search devices by keyword (searches id, host, name).

        Args:
            keyword: Search keyword

        Returns:
            List of matching devices
        """
        pattern = f"%{keyword}%"
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM devices
                WHERE id LIKE ? OR host LIKE ? OR name LIKE ?
                ORDER BY id
            """, (pattern, pattern, pattern)).fetchall()

        return [self._row_to_device(row) for row in rows]

    def close(self):
        """Close database connection"""
        if hasattr(self._local, 'connection'):
            self._local.connection.close()
            del self._local.connection