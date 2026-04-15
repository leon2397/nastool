"""
nastool Message Internationalization

Unified error and status messages with multi-language support.

Usage:
    from messages import msg

    print(msg("check.passed", check_id="cpu"))
    # Output: ✅ cpu: Passed

    print(msg("check.failed", check_id="disk", message="No space"))
    # Output: ❌ disk: Failed - No space
"""

from config import Config
from typing import Any, Optional

# Current language (default: "en")
_current_lang: str = "en"


# English messages (default)
MESSAGES_EN = {
    # Check results
    "check.passed": "✅ {check_id}: Passed",
    "check.failed": "❌ {check_id}: Failed - {message}",
    "check.warning": "⚠️ {check_id}: Warning - {message}",
    "check.skipped": "⏭️ {check_id}: Skipped - {message}",
    "check.running": "🔍 Running check: {check_id}",
    # Fix results
    "fix.applied": "✅ Fix applied: {fix_id}",
    "fix.failed": "❌ Fix failed: {fix_id} - {error}",
    "fix.skipped": "⏭️ Fix skipped: {fix_id}",
    "fix.confirm": "Apply fix '{fix_id}'? [y/N] ",
    # Device detection
    "device.detected": "📱 Detected device: {name} (profile: {profile})",
    "device.unknown": "❓ Unknown device, using generic profile",
    "device.profile_loaded": "📋 Loaded profile: {profile}",
    "device.profile_not_found": "❌ Profile not found: {profile}",
    # Diagnosis
    "diagnosis.start": "🔍 Starting diagnosis...",
    "diagnosis.complete": "✅ Diagnosis complete",
    "diagnosis.score": "📊 Health Score: {score}/100",
    "diagnosis.summary": "Summary: {passed} passed, {warnings} warnings, {failed} failed",
    # Monitoring
    "monitor.start": "📊 Starting monitoring daemon (interval: {interval}s)",
    "monitor.stop": "🛑 Monitoring daemon stopped",
    "monitor.check": "🔍 Running scheduled check...",
    "monitor.alert": "🚨 Alert: {message}",
    # Web/API
    "web.start": "🌐 Starting web dashboard on {url}",
    "api.request": "📥 {method} {path}",
    "api.error": "❌ API error: {error}",
    # Network
    "network.connected": "✅ Network: Connected",
    "network.disconnected": "❌ Network: Disconnected",
    "network.timeout": "⏱️ Network: Timeout ({timeout}s)",
    "network.nas_reachable": "✅ NAS backend reachable: {url}",
    "network.nas_unreachable": "❌ NAS backend unreachable: {url}",
    # Storage
    "storage.disk_ok": "✅ Disk: {free_gb}GB free of {total_gb}GB",
    "storage.disk_low": "⚠️ Disk low: {free_gb}GB free (threshold: {threshold}GB)",
    "storage.disk_critical": "❌ Disk critical: {free_gb}GB free",
    "storage.write_speed": "📝 Write speed: {speed} MB/s",
    "storage.path_exists": "✅ Path exists: {path}",
    "storage.path_missing": "❌ Path missing: {path}",
    # System
    "system.python_ok": "✅ Python: {version}",
    "system.python_old": "⚠️ Python version old: {version} (need {required})",
    "system.memory_ok": "✅ Memory: {available_gb}GB available of {total_gb}GB",
    "system.memory_low": "⚠️ Memory low: {available_gb}GB available",
    "system.temp_ok": "✅ Temperature: {temp}°C",
    "system.temp_high": "⚠️ Temperature high: {temp}°C",
    # AI/GPU
    "ai.gpu_detected": "✅ GPU detected: {name}",
    "ai.gpu_not_found": "❌ No GPU detected",
    "ai.driver_ok": "✅ {driver}: {version}",
    "ai.driver_old": "⚠️ {driver} old: {version} (latest: {latest})",
    "ai.driver_missing": "❌ {driver}: Not installed",
    # Security
    "security.firewall_ok": "✅ Firewall: Active",
    "security.firewall_inactive": "⚠️ Firewall: Inactive",
    "security.ssh_ok": "✅ SSH: Root login disabled",
    "security.ssh_insecure": "⚠️ SSH: Root login enabled",
    # Errors
    "error.unknown": "❌ Unknown error: {error}",
    "error.permission": "❌ Permission denied: {action}",
    "error.not_found": "❌ Not found: {item}",
    "error.timeout": "⏱️ Timeout: {operation}",
    "error.config": "❌ Config error: {message}",
    # Progress
    "progress.checking": "🔍 Checking {item}...",
    "progress.fixing": "🔧 Fixing {item}...",
    "progress.done": "✅ Done",
    # Registration
    "register.start": "📡 Registering to NAS backend: {url}",
    "register.success": "✅ Device registered successfully",
    "register.failed": "❌ Registration failed: {error}",
}

# Chinese messages
MESSAGES_ZH = {
    # Check results
    "check.passed": "✅ {check_id}: 通过",
    "check.failed": "❌ {check_id}: 失败 - {message}",
    "check.warning": "⚠️ {check_id}: 警告 - {message}",
    "check.skipped": "⏭️ {check_id}: 跳过 - {message}",
    "check.running": "🔍 正在检查: {check_id}",
    # Fix results
    "fix.applied": "✅ 修复成功: {fix_id}",
    "fix.failed": "❌ 修复失败: {fix_id} - {error}",
    "fix.skipped": "⏭️ 跳过修复: {fix_id}",
    "fix.confirm": "应用修复 '{fix_id}'? [y/N] ",
    # Device detection
    "device.detected": "📱 检测到设备: {name} (配置: {profile})",
    "device.unknown": "❓ 未知设备，使用通用配置",
    "device.profile_loaded": "📋 已加载配置: {profile}",
    "device.profile_not_found": "❌ 配置未找到: {profile}",
    # Diagnosis
    "diagnosis.start": "🔍 开始诊断...",
    "diagnosis.complete": "✅ 诊断完成",
    "diagnosis.score": "📊 健康评分: {score}/100",
    "diagnosis.summary": "汇总: {passed} 通过, {warnings} 警告, {failed} 失败",
    # Network
    "network.connected": "✅ 网络: 已连接",
    "network.disconnected": "❌ 网络: 未连接",
    "network.timeout": "⏱️ 网络: 超时 ({timeout}s)",
    "network.nas_reachable": "✅ NAS后端可达: {url}",
    "network.nas_unreachable": "❌ NAS后端不可达: {url}",
    # Storage
    "storage.disk_ok": "✅ 磁盘: {free_gb}GB 可用 / {total_gb}GB",
    "storage.disk_low": "⚠️ 磁盘空间不足: {free_gb}GB 可用 (阈值: {threshold}GB)",
    "storage.disk_critical": "❌ 磁盘空间严重不足: {free_gb}GB 可用",
    # System
    "system.python_ok": "✅ Python: {version}",
    "system.memory_ok": "✅ 内存: {available_gb}GB 可用 / {total_gb}GB",
    # Errors
    "error.unknown": "❌ 未知错误: {error}",
    "error.permission": "❌ 权限不足: {action}",
    "error.not_found": "❌ 未找到: {item}",
}

# Message bundles by language
MESSAGES = {
    "en": MESSAGES_EN,
    "zh": MESSAGES_ZH,
}


def set_language(lang: str) -> None:
    """Set the current language for messages.

    Args:
        lang: Language code ("en" or "zh")
    """
    global _current_lang
    if lang in MESSAGES:
        _current_lang = lang


def msg(key: str, lang: Optional[str] = None, **kwargs: Any) -> str:
    language = lang or _current_lang
    messages = MESSAGES.get(language, MESSAGES_EN)

    template = messages.get(key, MESSAGES_EN.get(key, f"[{key}]"))

    try:
        return template.format(**kwargs)
    except KeyError as e:
        # Missing parameter, return template as-is
        return template


def get_message(key: str, lang: Optional[str] = None) -> str:
    language = lang or _current_lang
    messages = MESSAGES.get(language, MESSAGES_EN)
    return messages.get(key, MESSAGES_EN.get(key, f"[{key}]"))


def list_messages(lang: str = "en") -> dict:
    """List all messages for a language."""
    return MESSAGES.get(lang, MESSAGES_EN).copy()
