"""
Scene Presets for nastool

Pre-configured diagnostic scenarios for different use cases.

Features:
- 5 predefined scenes (quick/daily/full/ai/storage)
- Auto-select checks based on scene
- Auto-set timeouts
- Easy one-line commands

Usage:
    # Quick check (30 seconds)
    python arm_diagnose.py --scene quick

    # Daily patrol (2 minutes)
    python arm_diagnose.py --scene daily

    # Full diagnostic (5 minutes)
    python arm_diagnose.py --scene full

    # AI focused
    python arm_diagnose.py --scene ai

    # Storage focused
    python arm_diagnose.py --scene storage
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from logger import get_logger

logger = get_logger(__name__)


class SceneType(Enum):
    """Predefined scene types"""

    QUICK = "quick"  # 30 seconds, basic checks
    DAILY = "daily"  # 2 minutes, routine patrol
    FULL = "full"  # 5 minutes, deep diagnostic
    AI = "ai"  # AI focused
    STORAGE = "storage"  # Storage focused


@dataclass
class SceneConfig:
    """Configuration for a diagnostic scene"""

    name: str
    description: str
    estimated_time: str
    checks: List[str]  # Check categories to run
    skip: List[str] = field(default_factory=list)  # Checks to skip
    timeout: int = 300  # Overall timeout in seconds
    benchmark: bool = False  # Run benchmarks
    fix: bool = False  # Auto-fix issues
    output_format: str = "terminal"  # terminal/json/html

    def get_summary(self) -> str:
        """Get one-line summary"""
        return f"{self.name} ({self.estimated_time}): {self.description}"


# Predefined scenes
SCENES: Dict[SceneType, SceneConfig] = {
    SceneType.QUICK: SceneConfig(
        name="快速检查",
        description="30秒快速诊断，适合日常检查",
        estimated_time="30秒",
        checks=[
            "device",  # CPU/Memory basic
            "disk_space",  # Disk space only
            "network_basic",  # Ping test
        ],
        skip=["benchmark", "write_speed", "ai_accel", "security"],
        timeout=60,
        benchmark=False,
    ),
    SceneType.DAILY: SceneConfig(
        name="日常巡检",
        description="2分钟日常巡检，覆盖主要健康指标",
        estimated_time="2分钟",
        checks=[
            "device",  # CPU/Memory/Temperature
            "storage",  # Disk + Write speed
            "network",  # Network + NAS connectivity
            "ai_basic",  # AI status check
        ],
        skip=["benchmark", "security_deep"],
        timeout=180,
        benchmark=False,
    ),
    SceneType.FULL: SceneConfig(
        name="完整诊断",
        description="5分钟深度诊断，覆盖所有检查项",
        estimated_time="5分钟",
        checks=["device", "storage", "network", "ai", "security"],
        skip=[],
        timeout=600,
        benchmark=True,
    ),
    SceneType.AI: SceneConfig(
        name="AI 算力专项",
        description="GPU/NPU 深度检测，适合 AI 应用部署前检查",
        estimated_time="3分钟",
        checks=[
            "device",  # Basic device info
            "ai",  # Full AI check
            "ai_benchmark",  # AI benchmark
        ],
        skip=["storage", "network", "security"],
        timeout=300,
        benchmark=True,
    ),
    SceneType.STORAGE: SceneConfig(
        name="存储专项",
        description="磁盘健康深度检测，适合 NAS 部署前检查",
        estimated_time="3分钟",
        checks=[
            "device",
            "storage",  # Full storage check
            "disk_health",  # S.M.A.R.T.
            "write_benchmark",
        ],
        skip=["ai", "network", "security"],
        timeout=300,
        benchmark=True,
    ),
}


class SceneManager:
    """
    Manager for diagnostic scenes.

    Usage:
        manager = SceneManager()

        # Get scene config
        config = manager.get_scene("quick")

        # List all scenes
        scenes = manager.list_scenes()
    """

    def __init__(self):
        self.custom_scenes: Dict[str, SceneConfig] = {}

    def get_scene(self, scene_name: str) -> Optional[SceneConfig]:
        """
        Get scene configuration by name.

        Args:
            scene_name: Scene name (quick/daily/full/ai/storage)

        Returns:
            SceneConfig or None if not found
        """
        # Try predefined scenes
        try:
            scene_type = SceneType(scene_name.lower())
            return SCENES.get(scene_type)
        except ValueError:
            pass

        # Try custom scenes
        return self.custom_scenes.get(scene_name.lower())

    def list_scenes(self) -> List[SceneConfig]:
        """List all available scenes"""
        scenes = list(SCENES.values())
        scenes.extend(self.custom_scenes.values())
        return scenes

    def register_custom_scene(self, config: SceneConfig):
        """Register a custom scene"""
        key = config.name.lower().replace(" ", "_")
        self.custom_scenes[key] = config
        logger.info(f"Registered custom scene: {config.name}")

    def print_scene_menu(self) -> str:
        """Generate a formatted scene selection menu"""
        lines = ["", "=" * 60, "  请选择诊断场景", "=" * 60, ""]

        for i, scene in enumerate(self.list_scenes(), 1):
            lines.append(f"  [{i}] {scene.name}")
            lines.append(f"      {scene.description}")
            lines.append(f"      预计耗时：{scene.estimated_time}")
            lines.append(f"      检查项：{', '.join(scene.checks[:3])}")
            if len(scene.checks) > 3:
                lines.append(f"            ... 共 {len(scene.checks)} 项")
            lines.append("")

        lines.append("  [0] 返回主菜单")
        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)


def apply_scene_to_args(scene_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply scene configuration to command-line arguments.

    Args:
        scene_name: Scene name
        args: Original command-line arguments

    Returns:
        Modified arguments with scene settings applied
    """
    manager = SceneManager()
    scene = manager.get_scene(scene_name)

    if not scene:
        logger.warning(f"Scene not found: {scene_name}, using default")
        return args

    # Apply scene settings
    args["checks"] = scene.checks
    args["skip"] = scene.skip
    args["timeout"] = scene.timeout
    args["benchmark"] = scene.benchmark
    args["scene"] = scene_name

    logger.info(f"Applied scene: {scene.name} ({scene.estimated_time})")

    return args


if __name__ == "__main__":
    # Demo
    manager = SceneManager()

    print("=" * 60)
    print("nastool v3.0.6 场景模式")
    print("=" * 60)
    print()

    # List all scenes
    for scene in manager.list_scenes():
        print(f"• {scene.get_summary()}")
        print(f"  检查项: {', '.join(scene.checks)}")
        print(f"  超时: {scene.timeout}s, 基准测试: {scene.benchmark}")
        print()

    # Print menu
    print(manager.print_scene_menu())

    # Demo: apply scene
    print()
    print("示例：应用 'quick' 场景")
    args = {}
    args = apply_scene_to_args("quick", args)
    print(f"结果: {args}")
