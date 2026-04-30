"""
NASTool Compare Module

Provides device comparison and historical analysis.

Usage:
    from nastool_cli.compare import CompareAnalyzer

    analyzer = CompareAnalyzer()
    diff = analyzer.compare_devices("device1", "device2")
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, asdict

from nastool_core.device_manager import DeviceManager, Device
from nastool_common.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CheckDiff:
    """Difference in a single check between devices"""
    check_id: str
    check_name: str
    device1_value: Any
    device2_value: Any
    device1_severity: str
    device2_severity: str
    diff_type: str  # "severity_change", "value_change", "new", "removed"


@dataclass
class DeviceComparison:
    """Result of comparing two devices"""
    device1_id: str
    device2_id: str
    device1_score: int
    device2_score: int
    score_diff: int
    critical_diff: Tuple[int, int]  # (device1_count, device2_count)
    warning_diff: Tuple[int, int]
    check_diffs: List[CheckDiff]
    timestamp: str


@dataclass
class HistoryPoint:
    """A single point in history"""
    timestamp: str
    score: int
    critical_count: int
    warning_count: int


@dataclass
class HistoryComparison:
    """Result of comparing device history"""
    device_id: str
    current: HistoryPoint
    baseline: HistoryPoint
    trend: str  # "improving", "degrading", "stable"
    score_change: int
    history: List[HistoryPoint]


class CompareAnalyzer:
    """
    Device comparison and historical analysis.

    Features:
    - Compare two devices side-by-side
    - Compare device against historical baseline
    - Trend analysis
    - Ideal baseline comparison
    """

    def __init__(
        self,
        device_manager: Optional[DeviceManager] = None,
        history_db: Optional[str] = None
    ):
        """
        Initialize CompareAnalyzer.

        Args:
            device_manager: DeviceManager instance
            history_db: History database path
        """
        self.device_manager = device_manager or DeviceManager()
        self.history_db = history_db or str(
            Path.home() / ".nastool" / "history.db"
        )
        self._ensure_db()

    def _ensure_db(self):
        """Ensure history database exists"""
        Path(self.history_db).parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.history_db) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS diagnosis_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    score INTEGER,
                    critical_count INTEGER,
                    warning_count INTEGER,
                    info_count INTEGER,
                    passed_count INTEGER,
                    total_count INTEGER,
                    report_json TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_history_device
                    ON diagnosis_history(device_id);
                CREATE INDEX IF NOT EXISTS idx_history_time
                    ON diagnosis_history(timestamp);
            """)

    # ==================== Device Comparison ====================

    def compare_devices(
        self,
        device1_id: str,
        device2_id: str,
        results1: Optional[List[Any]] = None,
        results2: Optional[List[Any]] = None
    ) -> DeviceComparison:
        """
        Compare two devices.

        Args:
            device1_id: First device ID
            device2_id: Second device ID
            results1: Pre-loaded results for device1 (optional)
            results2: Pre-loaded results for device2 (optional)

        Returns:
            DeviceComparison object
        """
        # Load results if not provided
        if results1 is None:
            results1 = self._load_latest_results(device1_id)
        if results2 is None:
            results2 = self._load_latest_results(device2_id)

        # Calculate scores
        score1 = self._calculate_score(results1)
        score2 = self._calculate_score(results2)

        # Count severities
        critical1 = sum(1 for r in results1 if r.severity == "CRITICAL")
        critical2 = sum(1 for r in results2 if r.severity == "CRITICAL")
        warning1 = sum(1 for r in results1 if r.severity == "WARNING")
        warning2 = sum(1 for r in results2 if r.severity == "WARNING")

        # Find check differences
        check_diffs = self._find_check_diffs(results1, results2)

        return DeviceComparison(
            device1_id=device1_id,
            device2_id=device2_id,
            device1_score=score1,
            device2_score=score2,
            score_diff=score2 - score1,
            critical_diff=(critical1, critical2),
            warning_diff=(warning1, warning2),
            check_diffs=check_diffs,
            timestamp=datetime.now().isoformat()
        )

    def _find_check_diffs(
        self,
        results1: List[Any],
        results2: List[Any]
    ) -> List[CheckDiff]:
        """Find differences between two result sets"""
        diffs = []

        # Build lookup maps
        map1 = {r.check_id: r for r in results1}
        map2 = {r.check_id: r for r in results2}

        all_ids = set(map1.keys()) | set(map2.keys())

        for check_id in sorted(all_ids):
            r1 = map1.get(check_id)
            r2 = map2.get(check_id)

            if r1 is None:
                # New in device2
                diffs.append(CheckDiff(
                    check_id=check_id,
                    check_name=r2.name,
                    device1_value=None,
                    device2_value=r2.value,
                    device1_severity="N/A",
                    device2_severity=r2.severity,
                    diff_type="new"
                ))

            elif r2 is None:
                # Removed in device2
                diffs.append(CheckDiff(
                    check_id=check_id,
                    check_name=r1.name,
                    device1_value=r1.value,
                    device2_value=None,
                    device1_severity=r1.severity,
                    device2_severity="N/A",
                    diff_type="removed"
                ))

            elif r1.severity != r2.severity:
                # Severity changed
                diffs.append(CheckDiff(
                    check_id=check_id,
                    check_name=r1.name,
                    device1_value=r1.value,
                    device2_value=r2.value,
                    device1_severity=r1.severity,
                    device2_severity=r2.severity,
                    diff_type="severity_change"
                ))

            elif r1.value != r2.value:
                # Value changed
                diffs.append(CheckDiff(
                    check_id=check_id,
                    check_name=r1.name,
                    device1_value=r1.value,
                    device2_value=r2.value,
                    device1_severity=r1.severity,
                    device2_severity=r2.severity,
                    diff_type="value_change"
                ))

        return diffs

    # ==================== History Comparison ====================

    def compare_history(
        self,
        device_id: str,
        days: int = 7
    ) -> HistoryComparison:
        """
        Compare current state against historical baseline.

        Args:
            device_id: Device ID
            days: Number of days to look back

        Returns:
            HistoryComparison object
        """
        # Load history
        history = self._load_history(device_id, days)

        if not history:
            # No history, return current as baseline
            current = self._get_current_point(device_id)
            return HistoryComparison(
                device_id=device_id,
                current=current,
                baseline=current,
                trend="stable",
                score_change=0,
                history=[current]
            )

        # Current is latest, baseline is oldest
        current = history[0]
        baseline = history[-1]

        # Determine trend
        score_change = current.score - baseline.score
        if score_change > 5:
            trend = "improving"
        elif score_change < -5:
            trend = "degrading"
        else:
            trend = "stable"

        return HistoryComparison(
            device_id=device_id,
            current=current,
            baseline=baseline,
            trend=trend,
            score_change=score_change,
            history=history
        )

    def _load_history(
        self,
        device_id: str,
        days: int
    ) -> List[HistoryPoint]:
        """Load history for a device"""
        since = (datetime.now() - timedelta(days=days)).isoformat()

        with sqlite3.connect(self.history_db) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT timestamp, score, critical_count, warning_count
                FROM diagnosis_history
                WHERE device_id = ? AND timestamp >= ?
                ORDER BY timestamp DESC
            """, (device_id, since)).fetchall()

        return [
            HistoryPoint(
                timestamp=row["timestamp"],
                score=row["score"],
                critical_count=row["critical_count"],
                warning_count=row["warning_count"]
            )
            for row in rows
        ]

    def _get_current_point(self, device_id: str) -> HistoryPoint:
        """Get current state as a history point"""
        results = self._load_latest_results(device_id)
        score = self._calculate_score(results)
        critical = sum(1 for r in results if r.severity == "CRITICAL")
        warning = sum(1 for r in results if r.severity == "WARNING")

        return HistoryPoint(
            timestamp=datetime.now().isoformat(),
            score=score,
            critical_count=critical,
            warning_count=warning
        )

    # ==================== Ideal Baseline ====================

    def compare_ideal(
        self,
        device_id: str,
        device_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Compare device against ideal baseline.

        Args:
            device_id: Device ID
            device_type: Device type (for baseline selection)

        Returns:
            Comparison result with gaps to ideal
        """
        device = self.device_manager.get_device(device_id)
        if device is None:
            raise ValueError(f"Device not found: {device_id}")

        device_type = device_type or device.device_type or "generic"
        results = self._load_latest_results(device_id)

        # Get ideal baseline for device type
        baseline = self._get_ideal_baseline(device_type)

        # Calculate gaps
        gaps = []
        for check_id, ideal_value in baseline.items():
            result = next(
                (r for r in results if r.check_id == check_id),
                None
            )

            if result is None:
                continue

            if result.value != ideal_value:
                gaps.append({
                    "check_id": check_id,
                    "current": result.value,
                    "ideal": ideal_value,
                    "severity": result.severity
                })

        current_score = self._calculate_score(results)
        ideal_score = 100  # Ideal baseline assumes perfect score

        return {
            "device_id": device_id,
            "device_type": device_type,
            "current_score": current_score,
            "ideal_score": ideal_score,
            "gap": ideal_score - current_score,
            "gaps": gaps,
            "timestamp": datetime.now().isoformat()
        }

    def _get_baseline_config_path(self) -> Path:
        """Get baseline configuration file path"""
        config_dir = Path.home() / ".nastool"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "baselines.json"

    def _get_ideal_baseline(self, device_type: str) -> Dict[str, Any]:
        """Get ideal baseline for device type"""
        config_path = self._get_baseline_config_path()
        
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    baselines = json.load(f)
                if device_type in baselines:
                    return baselines[device_type]
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load baselines from {config_path}: {e}")
                # 回退到默认值
        
        # 初始化默认配置
        self._initialize_default_baselines()
        
        # 再次尝试加载
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    baselines = json.load(f)
                if device_type in baselines:
                    return baselines[device_type]
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load baselines after initialization: {e}")
        
        # 如果仍然失败，返回空字典
        return {}

    def _initialize_default_baselines(self) -> None:
        """Initialize default baselines configuration"""
        config_path = self._get_baseline_config_path()
        
        if config_path.exists():
            return
        
        # Default ideal baselines by device type
        default_baselines = {
            "rk3588": {
                "cpu_governor": "performance",
                "npu_freq": "1000000000",  # 1GHz
                "gpu_freq": "1000000000",
                "thermal_zone_0": 45,  # < 45°C ideal
            },
            "rk3568": {
                "cpu_governor": "performance",
                "npu_freq": "800000000",  # 800MHz
                "thermal_zone_0": 45,
            },
            "jetson": {
                "cpu_governor": "performance",
                "gpu_freq": "1300500000",  # Jetson default
                "thermal_zone_0": 50,
            },
            "generic": {
                "cpu_governor": "performance",
                "thermal_zone_0": 50,
            }
        }
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(default_baselines, f, indent=2, ensure_ascii=False)
            logger.info(f"Initialized default baselines in {config_path}")
        except IOError as e:
            logger.error(f"Failed to initialize default baselines: {e}")

    def save_baseline(self, device_type: str, baseline: Dict[str, Any]) -> bool:
        """
        Save baseline configuration for a device type.
        
        Args:
            device_type: Device type
            baseline: Baseline configuration
            
        Returns:
            bool: True if saved successfully
        """
        config_path = self._get_baseline_config_path()
        
        try:
            # Load existing baselines
            baselines = {}
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    baselines = json.load(f)
            
            # Update baseline
            baselines[device_type] = baseline
            
            # Save back
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(baselines, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved baseline for device type: {device_type}")
            return True
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to save baseline: {e}")
            return False

    def delete_baseline(self, device_type: str) -> bool:
        """
        Delete baseline configuration for a device type.
        
        Args:
            device_type: Device type
            
        Returns:
            bool: True if deleted successfully
        """
        config_path = self._get_baseline_config_path()
        
        if not config_path.exists():
            return False
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                baselines = json.load(f)
            
            if device_type in baselines:
                del baselines[device_type]
                
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(baselines, f, indent=2, ensure_ascii=False)
                
                logger.info(f"Deleted baseline for device type: {device_type}")
                return True
            
            return False
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to delete baseline: {e}")
            return False

    def list_baselines(self) -> Dict[str, Dict[str, Any]]:
        """
        List all baseline configurations.
        
        Returns:
            Dict[str, Dict[str, Any]]: All baselines
        """
        config_path = self._get_baseline_config_path()
        
        if not config_path.exists():
            self._initialize_default_baselines()
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                baselines = json.load(f)
            return baselines
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to list baselines: {e}")
            return {}

    def validate_baseline(self, baseline: Dict[str, Any]) -> bool:
        """
        Validate baseline configuration.
        
        Args:
            baseline: Baseline configuration
            
        Returns:
            bool: True if valid
        """
        if not isinstance(baseline, dict):
            return False
        
        # 基本验证
        for key, value in baseline.items():
            if not isinstance(key, str):
                return False
            # 值可以是字符串或数字
            if not isinstance(value, (str, int, float)):
                return False
        
        return True

    # ==================== Storage ====================

    def save_result(
        self,
        device_id: str,
        results: List[Any],
        score: Optional[int] = None
    ) -> None:
        """
        Save diagnosis result to history.

        Args:
            device_id: Device ID
            results: Check results
            score: Pre-calculated score (optional)
        """
        if score is None:
            score = self._calculate_score(results)

        critical = sum(1 for r in results if r.severity == "CRITICAL")
        warning = sum(1 for r in results if r.severity == "WARNING")
        info = sum(1 for r in results if r.severity == "INFO")
        passed = sum(1 for r in results if r.passed)
        total = len(results)

        # Serialize results
        report_json = json.dumps([
            {
                "check_id": r.check_id,
                "name": r.name,
                "severity": r.severity,
                "passed": r.passed,
                "value": str(r.value) if r.value else None,
            }
            for r in results
        ])

        with sqlite3.connect(self.history_db) as conn:
            conn.execute("""
                INSERT INTO diagnosis_history
                (device_id, timestamp, score, critical_count, warning_count,
                 info_count, passed_count, total_count, report_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                device_id,
                datetime.now().isoformat(),
                score,
                critical,
                warning,
                info,
                passed,
                total,
                report_json
            ))

    # ==================== Utilities ====================

    def _load_latest_results(self, device_id: str) -> List[Any]:
        """Load latest results from history"""
        with sqlite3.connect(self.history_db) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("""
                SELECT report_json
                FROM diagnosis_history
                WHERE device_id = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (device_id,)).fetchone()

            if row is None:
                return []

            # Deserialize
            data = json.loads(row["report_json"])
            # Convert back to simple objects
            from types import SimpleNamespace
            return [
                SimpleNamespace(
                    check_id=d["check_id"],
                    name=d["name"],
                    severity=d["severity"],
                    passed=d["passed"],
                    value=d.get("value")
                )
                for d in data
            ]

    def _calculate_score(self, results: List[Any]) -> int:
        """Calculate health score from results"""
        if not results:
            return 0

        total = len(results)
        passed = sum(1 for r in results if r.passed)
        critical = sum(1 for r in results if r.severity == "CRITICAL")
        warning = sum(1 for r in results if r.severity == "WARNING")

        score = int((passed / total) * 100)
        score -= critical * 10
        score -= warning * 3

        return max(0, min(100, score))
