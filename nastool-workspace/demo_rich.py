#!/usr/bin/env python3
"""
demo_rich.py - Rich输出效果演示

展示v4.0的美化输出效果。
"""

import sys
sys.path.insert(0, r'C:\tools416\nastool-common')
sys.path.insert(0, r'C:\tools416\nastool-core')
sys.path.insert(0, r'C:\tools416\nastool-reporters')

from nastool_reporters.rich_reporter import (
    RichReporter, 
    DiagnosisProgress,
    print_diagnosis_start,
    print_diagnosis_complete,
    print_error,
    print_warning,
    print_success,
    print_info
)
from rich.console import Console
from rich.table import Table
from rich import box

console = Console()

print("=" * 70)
console.print("[bold blue]NASTool v4.0 - Rich Output Demo[/bold blue]")
print("=" * 70)

# 1. 标题头
console.print("\n[bold]1. Header Panel[/bold]")
reporter = RichReporter()
reporter.print_header("NASTool v4.0", "ARM Device Diagnostic Toolkit")

# 2. 设备列表表格
console.print("\n[bold]2. Device Table[/bold]")
devices = [
    {"id": "rk3588-01", "host": "192.168.1.100", "type": "RK3588", "group": "prod", "status": "online"},
    {"id": "rk3568-02", "host": "192.168.1.101", "type": "RK3568", "group": "prod", "status": "online"},
    {"id": "jetson-03", "host": "192.168.1.102", "type": "Jetson", "group": "dev", "status": "offline"},
]
reporter.print_device_table(devices)

# 3. 检测结果
console.print("\n[bold]3. Check Results[/bold]")
results = [
    {"check_id": "cpu_temperature", "severity": "passed", "message": "45°C - Normal"},
    {"check_id": "memory_usage", "severity": "warning", "message": "85% - High"},
    {"check_id": "disk_space", "severity": "critical", "message": "95% - Critical"},
    {"check_id": "network_latency", "severity": "info", "message": "12ms - Good"},
]
for r in results:
    reporter.print_check_result(r)

# 4. 汇总面板
console.print("\n[bold]4. Summary Panel[/bold]")
reporter.print_summary_panel({
    "total": 93,
    "passed": 75,
    "warning": 12,
    "critical": 6,
    "score": 82
})

# 5. 消息类型
console.print("\n[bold]5. Message Types[/bold]")
print_error("Connection failed to 192.168.1.100")
print_warning("High memory usage detected")
print_success("Device registered successfully")
print_info("Starting batch diagnosis...")

# 6. 进度条演示
console.print("\n[bold]6. Progress Bar[/bold]")
import time
with DiagnosisProgress(100, "Running diagnosis...") as progress:
    for i in range(10):
        time.sleep(0.1)
        progress.update(10)

console.print("\n[bold green]Demo Complete![/bold green]")
print("=" * 70)
