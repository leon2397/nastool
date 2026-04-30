"""
NASTool Batch Diagnosis Module

Provides batch diagnosis across multiple devices.

Usage:
    from nastool_cli.batch import BatchDiagnosis

    batch = BatchDiagnosis()
    results = batch.run(["device1", "device2"], parallel=4)
"""

import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, asdict

# 处理依赖导入
try:
    from nastool_core.device_manager import DeviceManager, Device
    from nastool_common.logger import get_logger
    logger = get_logger(__name__)
except ImportError as e:
    # 提供友好的错误信息
    raise ImportError(
        f"Failed to import required modules: {e}\n"
        f"Please install the required packages: 'nastool-core' and 'nastool-common'"
    ) from e

logger = get_logger(__name__)


@dataclass
class BatchResult:
    """Result of a single device diagnosis in batch"""
    device_id: str
    success: bool
    score: Optional[int] = None
    critical_count: int = 0
    warning_count: int = 0
    error: Optional[str] = None
    duration_ms: int = 0
    timestamp: str = ""


@dataclass
class BatchSummary:
    """Summary of batch diagnosis"""
    total: int
    success: int
    failed: int
    results: List[BatchResult]
    duration_ms: int
    timestamp: str

    @property
    def success_rate(self) -> float:
        return self.success / self.total if self.total > 0 else 0.0


class BatchDiagnosis:
    """
    Batch diagnosis across multiple devices.

    Features:
    - Parallel execution with concurrency limit
    - Progress callback for real-time updates
    - Automatic retry on failure
    - Result aggregation and export
    """

    def __init__(
        self,
        device_manager: Optional[DeviceManager] = None,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ):
        """
        Initialize BatchDiagnosis.

        Args:
            device_manager: DeviceManager instance
            progress_callback: Callback for progress updates (device_id, current, total)
        """
        self.device_manager = device_manager or DeviceManager()
        self.progress_callback = progress_callback

    def run(
        self,
        device_ids: List[str],
        parallel: int = 4,
        timeout: int = 300,
        retry: int = 0,
        full_mode: bool = False
    ) -> BatchSummary:
        """
        Run batch diagnosis with robust error handling.

        Args:
            device_ids: List of device IDs to diagnose
            parallel: Maximum concurrent diagnoses
            timeout: Timeout per device in seconds
            retry: Number of retries on failure
            full_mode: Run full diagnosis (including benchmarks)

        Returns:
            BatchSummary with all results
        """
        start_time = time.time()
        results = []
        total = len(device_ids)

        # Run diagnoses with concurrency limit
        semaphore = asyncio.Semaphore(parallel)

        async def diagnose_one(device_id: str, index: int) -> BatchResult:
            async with semaphore:
                # Progress callback
                if self.progress_callback:
                    try:
                        self.progress_callback(device_id, index + 1, total)
                    except Exception as e:
                        logger.warning(f"Progress callback failed: {e}")

                # Run diagnosis with error handling
                try:
                    return await self._diagnose_device(
                        device_id, timeout, retry, full_mode
                    )
                except Exception as e:
                    # 捕获所有异常，确保单个设备失败不影响整体
                    logger.error(f"Unexpected error diagnosing {device_id}: {e}")
                    return BatchResult(
                        device_id=device_id,
                        success=False,
                        error=f"Unexpected error: {str(e)}",
                        duration_ms=int((time.time() - start_time) * 1000),
                        timestamp=datetime.now().isoformat()
                    )

        # Create async tasks
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            tasks = [
                diagnose_one(device_id, i)
                for i, device_id in enumerate(device_ids)
            ]
            results = loop.run_until_complete(asyncio.gather(*tasks))
        except Exception as e:
            # 捕获整个批量执行过程中的异常
            logger.error(f"Batch execution failed: {e}")
            # 确保至少返回一个包含错误信息的结果
            results = [
                BatchResult(
                    device_id=device_id,
                    success=False,
                    error=f"Batch execution failed: {str(e)}",
                    duration_ms=int((time.time() - start_time) * 1000),
                    timestamp=datetime.now().isoformat()
                )
                for device_id in device_ids
            ]
        finally:
            loop.close()

        # Calculate summary
        duration_ms = int((time.time() - start_time) * 1000)
        success = sum(1 for r in results if r.success)
        failed = total - success

        return BatchSummary(
            total=total,
            success=success,
            failed=failed,
            results=list(results),
            duration_ms=duration_ms,
            timestamp=datetime.now().isoformat()
        )

    async def _diagnose_device(
        self,
        device_id: str,
        timeout: int,
        retry: int,
        full_mode: bool
    ) -> BatchResult:
        """
        Diagnose a single device.

        Args:
            device_id: Device ID
            timeout: Timeout in seconds
            retry: Number of retries
            full_mode: Full diagnosis mode

        Returns:
            BatchResult
        """
        start_time = time.time()
        last_error = None

        for attempt in range(retry + 1):
            try:
                # Get device info
                device = self.device_manager.get_device(device_id)
                if device is None:
                    return BatchResult(
                        device_id=device_id,
                        success=False,
                        error="Device not found",
                        timestamp=datetime.now().isoformat()
                    )

                # Run diagnosis based on device type
                results = await self._run_device_diagnosis(
                    device, timeout, full_mode
                )

                # Calculate score
                score = self._calculate_score(results)
                critical = sum(1 for r in results if r.severity == "CRITICAL")
                warning = sum(1 for r in results if r.severity == "WARNING")

                duration_ms = int((time.time() - start_time) * 1000)

                return BatchResult(
                    device_id=device_id,
                    success=True,
                    score=score,
                    critical_count=critical,
                    warning_count=warning,
                    duration_ms=duration_ms,
                    timestamp=datetime.now().isoformat()
                )

            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"Diagnosis failed for {device_id} (attempt {attempt + 1}): {e}"
                )

        # All retries failed
        duration_ms = int((time.time() - start_time) * 1000)
        return BatchResult(
            device_id=device_id,
            success=False,
            error=last_error,
            duration_ms=duration_ms,
            timestamp=datetime.now().isoformat()
        )

    async def _run_device_diagnosis(
        self,
        device: Device,
        timeout: int,
        full_mode: bool
    ) -> List[Any]:
        """
        Run diagnosis for a device with timeout control.

        Args:
            device: Device object
            timeout: Timeout in seconds
            full_mode: Full diagnosis mode

        Returns:
            List of CheckResult

        Raises:
            asyncio.TimeoutError: If diagnosis exceeds timeout
            ConnectionError: If connection fails
        """
        # Determine detection method based on device metadata
        detection_type = device.metadata.get("detection_type", "http")

        async def run_diagnosis():
            if detection_type == "relay":
                # Relay Server mode
                try:
                    from nastool_adapters.relay_detector import create_relay_detector
                except ImportError as e:
                    raise ImportError(
                        f"Failed to import relay detector: {e}\n"
                        f"Please install 'nastool-adapters'"
                    ) from e

                relay_url = device.metadata.get("relay_url", "relay://localhost:18888")
                detector = create_relay_detector(relay_url)

                if not detector.connect():
                    raise ConnectionError(f"Failed to connect to relay: {relay_url}")

                return detector.run_diagnosis(device.id, full_mode=full_mode)

            else:
                # HTTP API mode
                try:
                    from nastool_adapters.http_detector import RemoteHTTPDetector
                except ImportError as e:
                    raise ImportError(
                        f"Failed to import HTTP detector: {e}\n"
                        f"Please install 'nastool-adapters'"
                    ) from e

                detector = RemoteHTTPDetector(device.host)

                if not detector.connect():
                    raise ConnectionError(f"Failed to connect to {device.host}")

                return detector.run_diagnosis(full_mode=full_mode)

        # 添加超时控制
        try:
            return await asyncio.wait_for(run_diagnosis(), timeout=timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Diagnosis timed out after {timeout} seconds")

    def _calculate_score(self, results: List[Any]) -> int:
        """Calculate health score from results"""
        if not results:
            return 0

        total = len(results)
        passed = sum(1 for r in results if r.passed)
        critical = sum(1 for r in results if r.severity == "CRITICAL")
        warning = sum(1 for r in results if r.severity == "WARNING")

        # Base score from pass rate
        score = int((passed / total) * 100)

        # Penalize critical/warning
        score -= critical * 10
        score -= warning * 3

        return max(0, min(100, score))

    def export_results(
        self,
        summary: BatchSummary,
        output_path: str,
        format: str = "json"
    ) -> None:
        """
        Export batch results to file.

        Args:
            summary: BatchSummary to export
            output_path: Output file path
            format: Export format (json/csv)
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if format == "json":
            import json
            with open(path, "w", encoding="utf-8") as f:
                json.dump(asdict(summary), f, indent=2, ensure_ascii=False)

        elif format == "csv":
            import csv
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "device_id", "success", "score",
                    "critical_count", "warning_count",
                    "error", "duration_ms", "timestamp"
                ])
                for r in summary.results:
                    writer.writerow([
                        r.device_id, r.success, r.score,
                        r.critical_count, r.warning_count,
                        r.error or "", r.duration_ms, r.timestamp
                    ])

        else:
            raise ValueError(f"Unknown format: {format}")


def parse_device_list(source: str) -> List[str]:
    """
    Parse device list from various sources.

    Args:
        source: Device list source
            - "@file.txt" - Read from file (one ID per line)
            - "@group" - All devices in group
            - "@all" - All registered devices
            - "id1,id2,id3" - Comma-separated IDs

    Returns:
        List of device IDs
    """
    dm = DeviceManager()

    if source.startswith("@"):
        target = source[1:]

        if target == "all":
            # All devices
            return [d.id for d in dm.list_devices()]

        elif target.endswith(".txt") or Path(target).exists():
            # File
            with open(target, "r", encoding="utf-8") as f:
                return [
                    line.strip()
                    for line in f
                    if line.strip() and not line.startswith("#")
                ]

        else:
            # Group name
            return [d.id for d in dm.list_devices(group=target)]

    else:
        # Comma-separated
        return [id.strip() for id in source.split(",") if id.strip()]
