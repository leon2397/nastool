"""
Offline Diagnostic Mode - 离线诊断模式增强

支持在无网络环境下运行诊断：
- 本地存储诊断结果
- 网络恢复后自动同步
- 离线报告管理
- 数据队列持久化

适用场景：
- 断网环境
- 网络不稳定
- 隐私要求高的环境
"""

import os
import json
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class OfflineReport:
    """离线诊断报告"""

    report_id: str  # 报告 ID
    device_id: str  # 设备 ID
    timestamp: float  # 时间戳
    data: Dict[str, Any]  # 诊断数据
    synced: bool = False  # 是否已同步
    sync_time: float = 0  # 同步时间
    sync_attempts: int = 0  # 同步尝试次数
    last_error: str = ""  # 最后错误信息

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "report_id": self.report_id,
            "device_id": self.device_id,
            "timestamp": self.timestamp,
            "data": self.data,
            "synced": self.synced,
            "sync_time": self.sync_time,
            "sync_attempts": self.sync_attempts,
            "last_error": self.last_error,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "OfflineReport":
        """从字典创建"""
        return cls(
            report_id=d["report_id"],
            device_id=d["device_id"],
            timestamp=d["timestamp"],
            data=d["data"],
            synced=d.get("synced", False),
            sync_time=d.get("sync_time", 0),
            sync_attempts=d.get("sync_attempts", 0),
            last_error=d.get("last_error", ""),
        )


@dataclass
class OfflineConfig:
    """离线模式配置"""

    enabled: bool = True  # 是否启用离线模式
    storage_path: str = "/var/lib/nastool/offline"  # 存储路径
    max_reports: int = 100  # 最大报告数量
    max_age_days: int = 30  # 最大保留天数
    auto_sync: bool = True  # 自动同步
    sync_interval: int = 300  # 同步间隔（秒）
    max_retry: int = 5  # 最大重试次数
    retry_delay: int = 60  # 重试延迟（秒）

    def to_dict(self) -> Dict:
        return asdict(self)


class OfflineStorage:
    """
    离线存储管理器

    管理离线诊断报告的存储、检索和同步。
    """

    # 存储文件名
    MANIFEST_FILE = "manifest.json"
    REPORTS_DIR = "reports"
    QUEUE_FILE = "sync_queue.json"

    def __init__(self, config: OfflineConfig = None):
        """
        初始化离线存储

        Args:
            config: 离线配置
        """
        self.config = config or OfflineConfig()
        self.storage_path = Path(self.config.storage_path)
        self.reports_path = self.storage_path / self.REPORTS_DIR

        # 确保目录存在
        self._ensure_directories()

        # 加载清单
        self.manifest = self._load_manifest()
        self.reports: Dict[str, OfflineReport] = self._load_reports()

        # 同步状态
        self.sync_in_progress = False
        self.last_sync_attempt = 0

    def _ensure_directories(self):
        """确保目录存在"""
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.reports_path.mkdir(parents=True, exist_ok=True)

    def _load_manifest(self) -> Dict:
        """加载清单"""
        manifest_path = self.storage_path / self.MANIFEST_FILE
        if manifest_path.exists():
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load manifest: {e}")

        return {
            "version": "3.0.7",
            "created": time.time(),
            "updated": time.time(),
            "total_reports": 0,
            "synced_reports": 0,
            "pending_reports": 0,
        }

    def _save_manifest(self):
        """保存清单"""
        self.manifest["updated"] = time.time()
        self.manifest["total_reports"] = len(self.reports)
        self.manifest["synced_reports"] = sum(1 for r in self.reports.values() if r.synced)
        self.manifest["pending_reports"] = (
            self.manifest["total_reports"] - self.manifest["synced_reports"]
        )

        manifest_path = self.storage_path / self.MANIFEST_FILE
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(self.manifest, f, indent=2)

    def _load_reports(self) -> Dict[str, OfflineReport]:
        """加载所有报告"""
        reports = {}

        for report_file in self.reports_path.glob("*.json"):
            try:
                with open(report_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    report = OfflineReport.from_dict(data)
                    reports[report.report_id] = report
            except Exception as e:
                logger.error(f"Failed to load report {report_file}: {e}")

        return reports

    def _generate_report_id(self, device_id: str, timestamp: float) -> str:
        """生成报告 ID"""
        data = f"{device_id}:{timestamp}:{time.time()}"
        return hashlib.md5(data.encode()).hexdigest()[:12]

    # ========== 报告管理 ==========

    def save_report(self, device_id: str, data: Dict[str, Any]) -> str:
        """
        保存诊断报告

        Args:
            device_id: 设备 ID
            data: 诊断数据

        Returns:
            报告 ID
        """
        timestamp = time.time()
        report_id = self._generate_report_id(device_id, timestamp)

        report = OfflineReport(
            report_id=report_id,
            device_id=device_id,
            timestamp=timestamp,
            data=data,
        )

        # 保存到内存
        self.reports[report_id] = report

        # 保存到文件
        report_path = self.reports_path / f"{report_id}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, indent=2)

        # 更新清单
        self._save_manifest()

        logger.info(f"Saved offline report: {report_id}")
        return report_id

    def get_report(self, report_id: str) -> Optional[OfflineReport]:
        """获取报告"""
        return self.reports.get(report_id)

    def get_pending_reports(self) -> List[OfflineReport]:
        """获取待同步的报告"""
        return [r for r in self.reports.values() if not r.synced]

    def get_synced_reports(self) -> List[OfflineReport]:
        """获取已同步的报告"""
        return [r for r in self.reports.values() if r.synced]

    def delete_report(self, report_id: str) -> bool:
        """删除报告"""
        if report_id in self.reports:
            del self.reports[report_id]

            # 删除文件
            report_path = self.reports_path / f"{report_id}.json"
            if report_path.exists():
                report_path.unlink()

            self._save_manifest()
            return True
        return False

    def mark_synced(self, report_id: str) -> bool:
        """标记报告为已同步"""
        if report_id in self.reports:
            report = self.reports[report_id]
            report.synced = True
            report.sync_time = time.time()

            # 更新文件
            report_path = self.reports_path / f"{report_id}.json"
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report.to_dict(), f, indent=2)

            self._save_manifest()
            return True
        return False

    def mark_sync_failed(self, report_id: str, error: str) -> bool:
        """标记同步失败"""
        if report_id in self.reports:
            report = self.reports[report_id]
            report.sync_attempts += 1
            report.last_error = error

            # 更新文件
            report_path = self.reports_path / f"{report_id}.json"
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report.to_dict(), f, indent=2)

            return True
        return False

    # ========== 清理 ==========

    def cleanup_old_reports(self) -> int:
        """
        清理过期报告

        Returns:
            删除的报告数量
        """
        cutoff = time.time() - (self.config.max_age_days * 86400)
        deleted = 0

        for report_id, report in list(self.reports.items()):
            if report.timestamp < cutoff:
                self.delete_report(report_id)
                deleted += 1

        if deleted > 0:
            logger.info(f"Cleaned up {deleted} old reports")

        return deleted

    def cleanup_excess_reports(self) -> int:
        """
        清理超量报告（保留最新的）

        Returns:
            删除的报告数量
        """
        if len(self.reports) <= self.config.max_reports:
            return 0

        # 按时间排序
        sorted_reports = sorted(self.reports.values(), key=lambda r: r.timestamp, reverse=True)

        # 删除多余的
        to_delete = sorted_reports[self.config.max_reports :]
        deleted = 0

        for report in to_delete:
            self.delete_report(report.report_id)
            deleted += 1

        if deleted > 0:
            logger.info(f"Cleaned up {deleted} excess reports")

        return deleted

    # ========== 同步 ==========

    def sync_pending_reports(self, upload_func) -> Dict[str, bool]:
        """
        同步待上传的报告

        Args:
            upload_func: 上传函数，接收 report_id 和 data，返回 bool

        Returns:
            同步结果字典 {report_id: success}
        """
        if self.sync_in_progress:
            logger.warning("Sync already in progress")
            return {}

        self.sync_in_progress = True
        self.last_sync_attempt = time.time()

        results = {}
        pending = self.get_pending_reports()

        logger.info(f"Syncing {len(pending)} pending reports")

        for report in pending:
            # 检查重试次数
            if report.sync_attempts >= self.config.max_retry:
                logger.warning(f"Report {report.report_id} exceeded max retries")
                continue

            try:
                success = upload_func(report.report_id, report.data)

                if success:
                    self.mark_synced(report.report_id)
                    results[report.report_id] = True
                    logger.info(f"Synced report: {report.report_id}")
                else:
                    self.mark_sync_failed(report.report_id, "Upload failed")
                    results[report.report_id] = False

            except Exception as e:
                self.mark_sync_failed(report.report_id, str(e))
                results[report.report_id] = False
                logger.error(f"Failed to sync report {report.report_id}: {e}")

        self.sync_in_progress = False
        return results

    # ========== 状态 ==========

    def get_status(self) -> Dict:
        """获取离线存储状态"""
        return {
            "enabled": self.config.enabled,
            "storage_path": str(self.storage_path),
            "total_reports": len(self.reports),
            "pending_reports": len(self.get_pending_reports()),
            "synced_reports": len(self.get_synced_reports()),
            "oldest_report": min((r.timestamp for r in self.reports.values()), default=0),
            "newest_report": max((r.timestamp for r in self.reports.values()), default=0),
            "sync_in_progress": self.sync_in_progress,
            "last_sync_attempt": self.last_sync_attempt,
        }


class OfflineModeManager:
    """
    离线模式管理器

    管理在线/离线模式切换。
    """

    def __init__(self, storage: OfflineStorage = None, config: OfflineConfig = None):
        self.storage = storage or OfflineStorage(config)
        self.config = self.storage.config

        # 网络状态
        self.is_online = True
        self.last_online_check = 0
        self.online_check_interval = 60  # 60秒检查一次

    def check_online(self) -> bool:
        """
        检查网络连接

        Returns:
            True 如果在线
        """
        # 节流检查
        if time.time() - self.last_online_check < self.online_check_interval:
            return self.is_online

        self.last_online_check = time.time()

        try:
            import urllib.request

            urllib.request.urlopen("https://www.google.com", timeout=5)
            self.is_online = True
            return True
        except Exception as e:
            self.is_online = False
            return False

    def should_use_offline_mode(self) -> bool:
        """判断是否应使用离线模式"""
        if not self.config.enabled:
            return False

        return not self.check_online()

    def save_diagnostic_result(self, device_id: str, data: Dict) -> str:
        """
        保存诊断结果

        自动选择在线/离线模式

        Args:
            device_id: 设备 ID
            data: 诊断数据

        Returns:
            报告 ID
        """
        return self.storage.save_report(device_id, data)

    def try_sync(self, upload_func) -> Dict[str, bool]:
        """
        尝试同步离线数据

        Args:
            upload_func: 上传函数

        Returns:
            同步结果
        """
        if not self.check_online():
            logger.info("Offline, skipping sync")
            return {}

        return self.storage.sync_pending_reports(upload_func)


def create_offline_storage(storage_path: str = None) -> OfflineStorage:
    """
    创建离线存储实例

    Args:
        storage_path: 存储路径

    Returns:
        离线存储实例
    """
    config = OfflineConfig()
    if storage_path:
        config.storage_path = storage_path

    return OfflineStorage(config)


if __name__ == "__main__":
    # 测试
    print("=== Offline Storage Test ===\n")

    # 创建测试存储
    storage = create_offline_storage("/tmp/nastool_offline_test")

    # 保存测试报告
    report_id = storage.save_report(
        "test-device-001",
        {
            "health_score": 95,
            "cpu_usage": 25.5,
            "memory_usage": 60.2,
            "disk_usage": 45.8,
        },
    )
    print(f"Saved report: {report_id}")

    # 获取状态
    status = storage.get_status()
    print(f"\nStorage status:")
    print(f"  Total reports: {status['total_reports']}")
    print(f"  Pending: {status['pending_reports']}")

    # 获取待同步报告
    pending = storage.get_pending_reports()
    print(f"\nPending reports: {len(pending)}")
    for report in pending:
        print(f"  - {report.report_id}: score={report.data.get('health_score')}")

    print("\n=== Test Complete ===")
