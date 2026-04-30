"""
checks/base.py - Base classes for all checks
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List


class CheckSeverity(Enum):
    """Check result severity levels"""

    INFO = "info"  # Informational, no action needed
    WARNING = "warning"  # Warning, should fix but not critical
    CRITICAL = "critical"  # Critical, must fix before proceeding
    PASSED = "passed"  # Check passed


class CheckCategory(Enum):
    """Check categories for organization"""

    SYSTEM = "system"
    NETWORK = "network"
    STORAGE = "storage"
    AI = "ai"
    SECURITY = "security"
    NAS = "nas"
    USB = "usb"  # v5.0.3


@dataclass
class CheckResult:
    """Result of a single check"""

    check_id: str  # Unique identifier: "python_version"
    category: CheckCategory  # Category for grouping
    severity: CheckSeverity  # Result severity
    passed: bool  # True if check passed
    title: str  # Human-readable title: "Python Version"
    current: str  # Current state: "3.6.9"
    expected: str  # Expected state: "3.8+"
    message: str  # Detailed message
    fix_available: bool = False  # Can be auto-fixed?
    fix_id: Optional[str] = None  # Corresponding fix ID
    fix_command: Optional[str] = None  # Command to fix
    fix_description: Optional[str] = None  # Human-readable fix description
    fix_risk: str = "low"  # Fix risk: low/medium/high
    url: Optional[str] = None  # Reference URL
    details: dict = field(default_factory=dict)  # Additional details


@dataclass
class CheckSummary:
    """Summary of all check results"""

    total: int = 0
    passed: int = 0
    warnings: int = 0
    critical: int = 0
    info: int = 0
    score: int = 0  # 0-100
    results: List[CheckResult] = field(default_factory=list)

    def add_result(self, result: CheckResult):
        """Add a result and update counters"""
        self.results.append(result)
        self.total += 1

        if result.passed:
            self.passed += 1
        else:
            # 归一化 severity：支持枚举和字符串
            sev = result.severity
            if isinstance(sev, str):
                m = {"info": CheckSeverity.INFO, "warning": CheckSeverity.WARNING,
                     "critical": CheckSeverity.CRITICAL, "passed": CheckSeverity.PASSED}
                sev = m.get(sev.lower(), CheckSeverity.INFO)
            if sev == CheckSeverity.WARNING:
                self.warnings += 1
            elif sev == CheckSeverity.CRITICAL:
                self.critical += 1
            elif sev == CheckSeverity.INFO:
                self.info += 1

    def calculate_score(self):
        """Calculate overall health score (0-100) [legacy]"""
        if self.total == 0:
            return 0

        # Weighted scoring
        passed_weight = 100
        warning_weight = 70
        critical_weight = 0

        total_score = (
            self.passed * passed_weight
            + self.warnings * warning_weight
            + self.critical * critical_weight
        )
        max_score = self.total * passed_weight

        self.score = int((total_score / max_score) * 100) if max_score > 0 else 0
        return self.score

    def get_health_report(self, previous_score: int = None) -> "HealthReport":
        """
        Calculate detailed health score using HealthScorer (v4.0.2).
        Returns a HealthReport with category-level scores and recommendations.
        """
        from utils.health_scorer import calculate_health_score
        report = calculate_health_score(self.results, previous_score)
        self.score = report.overall_score
        return report


class Check(ABC):
    """Abstract base class for all checks"""

    # Subclasses should override these
    check_id: str = "base_check"
    category: CheckCategory = CheckCategory.SYSTEM
    title: str = "Base Check"
    description: str = "Base check class"

    @abstractmethod
    def run(self) -> CheckResult:
        """
        Run the check and return result.
        Must be implemented by subclasses.
        """
        pass

    def _run_command(self, cmd: str, timeout: int = 10) -> str:
        """Helper to run shell command"""
        import subprocess

        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, errors="replace", timeout=timeout
            )
            return result.stdout.strip()
        except Exception as e:
            return ""

    def _read_file(self, path: str) -> str:
        """Helper to read file contents"""
        try:
            with open(path, "r") as f:
                return f.read().strip()
        except Exception as e:
            return ""

    def _file_exists(self, path: str) -> bool:
        """Check if file exists"""
        import os

        return os.path.exists(path)

    def _command_exists(self, cmd: str) -> bool:
        """Check if command exists"""
        import shutil

        return shutil.which(cmd) is not None
