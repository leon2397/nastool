"""
Setup Wizard for nastool

Interactive configuration wizard for first-time users.

Features:
- Guided setup with sensible defaults
- Interactive prompts
- Configuration validation
- Auto-detect system settings

Usage:
    python arm_diagnose.py --setup
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import os
import sys
from pathlib import Path
from nastool_common.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SetupQuestion:
    """Single setup question"""

    key: str  # Config key
    question: str  # Question text
    default: Any  # Default value
    validator: callable = None  # Validation function
    description: str = ""  # Help text
    required: bool = True  # Is required field


# Default configuration template
DEFAULT_CONFIG = {
    "nas": {"backend_url": "http://localhost:8000", "device_name": "", "register": True},
    "diagnostics": {"timeout": 300, "benchmark": False, "scene": "daily"},
    "thresholds": {
        "cpu_warning": 80,
        "cpu_critical": 95,
        "memory_warning": 85,
        "memory_critical": 95,
        "disk_warning": 85,
        "disk_critical": 95,
        "temp_warning": 70,
        "temp_critical": 85,
    },
    "alerts": {"enabled": True, "interval_minutes": 30},
    "output": {"format": "terminal", "color": True, "verbose": False},
}


class SetupWizard:
    """
    Interactive setup wizard for nastool configuration.

    Usage:
        wizard = SetupWizard()
        config = wizard.run()
        wizard.save_config(config, "config.yaml")
    """

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self.config = {}

        # Define setup questions
        self.questions = [
            # NAS Backend
            SetupQuestion(
                key="nas.backend_url",
                question="NAS 后端地址",
                default="http://localhost:8000",
                description="NAS 后端服务的 URL 地址",
                validator=self._validate_url,
            ),
            SetupQuestion(
                key="nas.device_name",
                question="设备名称",
                default=self._detect_hostname(),
                description="设备在 NAS 中的显示名称",
                required=False,
            ),
            SetupQuestion(
                key="nas.register",
                question="自动注册到 NAS 后端",
                default=True,
                description="诊断完成后自动注册设备",
            ),
            # Diagnostics
            SetupQuestion(
                key="diagnostics.timeout",
                question="诊断超时时间（秒）",
                default=300,
                validator=self._validate_positive_int,
            ),
            SetupQuestion(key="diagnostics.benchmark", question="默认运行基准测试", default=False),
            SetupQuestion(
                key="diagnostics.scene",
                question="默认诊断场景",
                default="daily",
                validator=lambda x: x in ["quick", "daily", "full", "ai", "storage"],
            ),
            # Thresholds
            SetupQuestion(
                key="thresholds.cpu_warning",
                question="CPU 使用率告警阈值 (%)",
                default=80,
                validator=self._validate_percentage,
            ),
            SetupQuestion(
                key="thresholds.cpu_critical",
                question="CPU 使用率严重阈值 (%)",
                default=95,
                validator=self._validate_percentage,
            ),
            SetupQuestion(
                key="thresholds.memory_warning",
                question="内存使用率告警阈值 (%)",
                default=85,
                validator=self._validate_percentage,
            ),
            SetupQuestion(
                key="thresholds.memory_critical",
                question="内存使用率严重阈值 (%)",
                default=95,
                validator=self._validate_percentage,
            ),
            SetupQuestion(
                key="thresholds.disk_warning",
                question="磁盘使用率告警阈值 (%)",
                default=85,
                validator=self._validate_percentage,
            ),
            SetupQuestion(
                key="thresholds.disk_critical",
                question="磁盘使用率严重阈值 (%)",
                default=95,
                validator=self._validate_percentage,
            ),
            # Alerts
            SetupQuestion(key="alerts.enabled", question="启用告警", default=True),
            SetupQuestion(
                key="alerts.interval_minutes",
                question="检查间隔（分钟）",
                default=30,
                validator=self._validate_positive_int,
            ),
            # Output
            SetupQuestion(key="output.color", question="启用彩色输出", default=True),
            SetupQuestion(key="output.verbose", question="详细输出模式", default=False),
        ]

    def _detect_hostname(self) -> str:
        """Detect system hostname"""
        try:
            import socket

            return socket.gethostname()
        except Exception as e:
            return "arm-device"

    def _validate_url(self, url: str) -> bool:
        """Validate URL format"""
        return url.startswith("http://") or url.startswith("https://")

    def _validate_percentage(self, value: int) -> bool:
        """Validate percentage value"""
        return 0 <= value <= 100

    def _validate_positive_int(self, value: int) -> bool:
        """Validate positive integer"""
        return value > 0

    def _get_nested_value(self, d: dict, key: str) -> Any:
        """Get nested dictionary value"""
        keys = key.split(".")
        for k in keys:
            if isinstance(d, dict) and k in d:
                d = d[k]
            else:
                return None
        return d

    def _set_nested_value(self, d: dict, key: str, value: Any):
        """Set nested dictionary value"""
        keys = key.split(".")
        for k in keys[:-1]:
            if k not in d:
                d[k] = {}
            d = d[k]
        d[keys[-1]] = value

    def _ask_question(self, question: SetupQuestion) -> Any:
        """
        Ask user a question and get response.

        Returns:
            User's answer or default value
        """
        print()
        print(f"  {question.question}")
        if question.description:
            print(f"  ({question.description})")

        # Show default
        default_str = str(question.default)
        if isinstance(question.default, bool):
            default_str = "Y/n" if question.default else "y/N"

        print(f"  默认: {default_str}")
        print()

        # Get input
        try:
            answer = input("  > ").strip()
        except EOFError:
            answer = ""

        # Use default if empty
        if not answer:
            return question.default

        # Convert type
        try:
            if isinstance(question.default, bool):
                return answer.lower() in ["y", "yes", "true", "1"]
            elif isinstance(question.default, int):
                return int(answer)
            elif isinstance(question.default, float):
                return float(answer)
            else:
                return answer
        except ValueError:
            print(f"  [!] 无效输入，使用默认值: {question.default}")
            return question.default

    def run(self, interactive: bool = True) -> Dict[str, Any]:
        """
        Run the setup wizard.

        Args:
            interactive: If True, ask questions; if False, use defaults

        Returns:
            Configuration dictionary
        """
        print()
        print("=" * 60)
        print("  nastool 配置向导")
        print("=" * 60)
        print()
        print("  欢迎使用 nastool！这个向导将帮助你配置诊断工具。")
        print("  按 Enter 使用默认值，或输入自定义值。")
        print()

        config = {}

        if interactive:
            for question in self.questions:
                answer = self._ask_question(question)

                # Validate
                if question.validator and not question.validator(answer):
                    print(f"  [!] 验证失败，使用默认值: {question.default}")
                    answer = question.default

                # Set value
                self._set_nested_value(config, question.key, answer)
        else:
            # Use defaults
            config = DEFAULT_CONFIG.copy()

        print()
        print("=" * 60)
        print("  [OK] 配置完成！")
        print("=" * 60)
        print()

        return config

    def save_config(self, config: Dict[str, Any], path: str = None) -> bool:
        """
        Save configuration to YAML file.

        Args:
            config: Configuration dictionary
            path: Output path (default: self.config_path)

        Returns:
            True if saved successfully
        """
        path = Path(path or self.config_path)

        try:
            # Try to import yaml
            try:
                import yaml
            except ImportError:
                print("  [!] PyYAML 未安装，使用 JSON 格式保存")
                import json

                with open(path.with_suffix(".json"), "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                return True

            # Save as YAML
            with open(path, "w", encoding="utf-8") as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

            print(f"  [OK] 配置已保存到: {path}")
            return True

        except Exception as e:
            print(f"  [X] 保存配置失败: {e}")
            return False

    def load_config(self, path: str = None) -> Optional[Dict[str, Any]]:
        """
        Load configuration from file.

        Args:
            path: Config file path

        Returns:
            Configuration dictionary or None if not found
        """
        path = Path(path or self.config_path)

        if not path.exists():
            return None

        try:
            # Try YAML first
            if path.suffix in [".yaml", ".yml"]:
                try:
                    import yaml

                    with open(path, "r", encoding="utf-8") as f:
                        return yaml.safe_load(f)
                except ImportError:
                    pass

            # Try JSON
            import json

            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)

        except Exception as e:
            print(f"  [X] 加载配置失败: {e}")
            return None


def run_setup(config_path: str = "config.yaml", interactive: bool = True) -> Dict[str, Any]:
    """
    Convenience function to run setup wizard.

    Args:
        config_path: Path to config file
        interactive: If True, ask questions; if False, use defaults

    Returns:
        Configuration dictionary
    """
    wizard = SetupWizard(config_path)
    config = wizard.run(interactive)
    wizard.save_config(config)
    return config


if __name__ == "__main__":
    # Demo
    print()
    print("配置向导演示（非交互模式）")
    print("-" * 60)

    wizard = SetupWizard()
    config = wizard.run(interactive=False)

    print()
    print("生成的配置：")
    print("-" * 60)

    import json

    print(json.dumps(config, indent=2, ensure_ascii=False))
