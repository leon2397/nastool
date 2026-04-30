"""
Action Suggestions System for nastool

Provides actionable suggestions for each detected issue.

Features:
- Concrete commands to fix issues
- Priority-based ordering
- Safety levels (safe/moderate/advanced)
- One-click execution support
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
from .logger import get_logger

logger = get_logger(__name__)


class SafetyLevel(Enum):
    """Safety level for suggestions"""

    SAFE = "safe"  # Can be executed without risk
    MODERATE = "moderate"  # May require confirmation
    ADVANCED = "advanced"  # Should be reviewed before execution


@dataclass
class ActionSuggestion:
    """Single action suggestion"""

    issue: str  # Issue description
    suggestion: str  # What to do
    command: Optional[str]  # Command to execute (if applicable)
    safety: SafetyLevel  # Safety level
    priority: int  # Higher = more important
    category: str  # e.g., "storage", "network", "ai"

    def is_executable(self) -> bool:
        """Check if this suggestion has a command"""
        return self.command is not None and len(self.command) > 0


# Pre-defined suggestions database
SUGGESTIONS_DB: Dict[str, ActionSuggestion] = {
    # Storage issues
    "disk_low_space": ActionSuggestion(
        issue="磁盘空间不足",
        suggestion="清理临时文件或旧日志",
        command="rm -rf /tmp/* /var/log/*.log",
        safety=SafetyLevel.MODERATE,
        priority=10,
        category="storage",
    ),
    "disk_almost_full": ActionSuggestion(
        issue="磁盘即将满",
        suggestion="立即清理磁盘空间",
        command="python arm_diagnose.py --fix --auto",
        safety=SafetyLevel.SAFE,
        priority=20,
        category="storage",
    ),
    # Memory issues
    "memory_high": ActionSuggestion(
        issue="内存使用率过高",
        suggestion="重启内存密集型服务",
        command="systemctl restart ai-nas",
        safety=SafetyLevel.MODERATE,
        priority=8,
        category="system",
    ),
    "memory_critical": ActionSuggestion(
        issue="内存严重不足",
        suggestion="释放内存或增加 swap",
        command="sync && echo 3 > /proc/sys/vm/drop_caches",
        safety=SafetyLevel.ADVANCED,
        priority=15,
        category="system",
    ),
    # CPU issues
    "cpu_high": ActionSuggestion(
        issue="CPU 使用率过高",
        suggestion="检查是否有异常进程",
        command="top -b -n 1 | head -20",
        safety=SafetyLevel.SAFE,
        priority=7,
        category="system",
    ),
    # Network issues
    "network_slow": ActionSuggestion(
        issue="网络延迟过高",
        suggestion="检查网络连接",
        command="ping -c 10 8.8.8.8",
        safety=SafetyLevel.SAFE,
        priority=5,
        category="network",
    ),
    "nas_unreachable": ActionSuggestion(
        issue="NAS 后端无法连接",
        suggestion="检查 NAS 服务状态",
        command="curl -s http://localhost:8000/health",
        safety=SafetyLevel.SAFE,
        priority=12,
        category="network",
    ),
    # AI issues
    "no_gpu": ActionSuggestion(
        issue="未检测到 GPU",
        suggestion="安装 GPU 驱动",
        command="nvidia-smi || echo 'NVIDIA 驱动未安装'",
        safety=SafetyLevel.SAFE,
        priority=6,
        category="ai",
    ),
    "no_cuda": ActionSuggestion(
        issue="CUDA 不可用",
        suggestion="安装 CUDA Toolkit",
        command="",  # Manual installation required
        safety=SafetyLevel.ADVANCED,
        priority=8,
        category="ai",
    ),
    # Permission issues
    "permission_denied": ActionSuggestion(
        issue="权限不足",
        suggestion="使用 sudo 或检查文件权限",
        command="ls -la",
        safety=SafetyLevel.SAFE,
        priority=4,
        category="system",
    ),
    # Config issues
    "config_missing": ActionSuggestion(
        issue="配置文件不存在",
        suggestion="运行配置向导创建配置",
        command="python arm_diagnose.py --setup",
        safety=SafetyLevel.SAFE,
        priority=9,
        category="config",
    ),
    # Service issues
    "service_down": ActionSuggestion(
        issue="服务未运行",
        suggestion="启动服务",
        command="systemctl start ai-nas",
        safety=SafetyLevel.SAFE,
        priority=11,
        category="system",
    ),
}


class SuggestionEngine:
    """
    Engine for generating actionable suggestions.

    Usage:
        engine = SuggestionEngine()
        suggestions = engine.suggest("disk_low_space")

        for s in suggestions:
            print(f"{s.issue}: {s.suggestion}")
    """

    def __init__(self):
        self.custom_suggestions: Dict[str, ActionSuggestion] = {}

    def register(self, key: str, suggestion: ActionSuggestion):
        """Register a custom suggestion"""
        self.custom_suggestions[key] = suggestion

    def suggest(self, key: str) -> Optional[ActionSuggestion]:
        """Get suggestion for a specific issue key"""
        # Check custom first
        if key in self.custom_suggestions:
            return self.custom_suggestions[key]

        # Check database
        if key in SUGGESTIONS_DB:
            return SUGGESTIONS_DB[key]

        return None

    def suggest_for_results(self, results: Dict[str, Any]) -> List[ActionSuggestion]:
        """
        Generate suggestions based on check results.

        Args:
            results: Dict with category -> {status, data}

        Returns:
            List of suggestions sorted by priority
        """
        suggestions = []

        for category, result in results.items():
            if result.get("status") == "ok":
                continue

            # Try to find matching suggestion
            key = f"{category}_{result.get('issue', 'unknown')}"
            suggestion = self.suggest(key)

            if suggestion:
                suggestions.append(suggestion)
            else:
                # Generic suggestion
                suggestions.append(
                    ActionSuggestion(
                        issue=result.get("message", f"{category} 检查失败"),
                        suggestion="运行 --fix 查看修复选项",
                        command="python arm_diagnose.py --fix",
                        safety=SafetyLevel.SAFE,
                        priority=1,
                        category=category,
                    )
                )

        # Sort by priority
        suggestions.sort(key=lambda x: x.priority, reverse=True)
        return suggestions

    def generate_fix_script(self, suggestions: List[ActionSuggestion]) -> str:
        """
        Generate a shell script to execute suggestions.

        Args:
            suggestions: List of executable suggestions

        Returns:
            Shell script content
        """
        lines = [
            "#!/bin/bash",
            "# nastool 自动修复脚本",
            "# 自动生成于 " + str(__import__("datetime").datetime.now()),
            "",
            "set -e  # 遇到错误即停止",
            "",
            "echo '>> 开始自动修复...'",
            "",
        ]

        for i, s in enumerate(suggestions):
            if not s.is_executable():
                continue

            safety_icon = {
                SafetyLevel.SAFE: "[OK]",
                SafetyLevel.MODERATE: "[!]",
                SafetyLevel.ADVANCED: "🔴",
            }.get(s.safety, "❓")

            lines.append(f"# {i + 1}. {s.issue}")
            lines.append(f"echo '{safety_icon} {s.suggestion}'")

            if s.safety == SafetyLevel.SAFE:
                lines.append(f"{s.command}")
            elif s.safety == SafetyLevel.MODERATE:
                lines.append(f"read -p '执行此命令? [y/N] ' confirm")
                lines.append(f'if [ "$confirm" = "y" ]; then')
                lines.append(f"  {s.command}")
                lines.append(f"fi")
            else:  # ADVANCED
                lines.append(f"echo '[!] 此操作需要手动确认：'")
                lines.append(f"echo '  {s.command}'")
                lines.append(f"read -p '确认执行? [y/N] ' confirm")
                lines.append(f'if [ "$confirm" = "y" ]; then')
                lines.append(f"  {s.command}")
                lines.append(f"fi")

            lines.append("")

        lines.append("echo '[OK] 修复完成！'")

        return "\n".join(lines)


if __name__ == "__main__":
    # Demo
    engine = SuggestionEngine()

    print("=" * 50)
    print("操作建议示例")
    print("=" * 50)
    print()

    # Simulate check results
    results = {
        "disk": {"status": "warning", "issue": "low_space", "message": "磁盘剩余 15%"},
        "memory": {"status": "ok", "message": "内存使用率 45%"},
        "ai": {"status": "error", "issue": "no_gpu", "message": "未检测到 GPU"},
    }

    suggestions = engine.suggest_for_results(results)

    for s in suggestions:
        icon = {SafetyLevel.SAFE: "[OK]", SafetyLevel.MODERATE: "[!]", SafetyLevel.ADVANCED: "🔴"}.get(
            s.safety, "❓"
        )

        print(f"{icon} {s.issue}")
        print(f"   建议：{s.suggestion}")
        if s.is_executable():
            print(f"   命令：{s.command}")
        print()

    print()
    print("生成的修复脚本：")
    print("-" * 50)
    print(engine.generate_fix_script(suggestions))
