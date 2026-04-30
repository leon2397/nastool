"""
commands/diagnose.py - 诊断命令（Rich美化版）
"""

import argparse
import sys
import time
from typing import Optional

from nastool_core import run_checks_parallel, CHECK_TIMEOUTS
from nastool_core.checks import list_checks
from nastool_reporters.rich_reporter import (
    RichReporter, 
    DiagnosisProgress,
    print_diagnosis_start,
    print_diagnosis_complete
)
from nastool_common.logger import get_logger

from . import Command, register_command

logger = get_logger(__name__)


@register_command(
    name="diagnose",
    help="Run system diagnosis",
    aliases=["d", "check"]
)
class DiagnoseCommand(Command):
    """诊断命令（v4.0 Rich美化版）"""
    
    def __init__(self):
        self.reporter = RichReporter()
    
    def add_arguments(self, parser: argparse.ArgumentParser):
        parser.add_argument("--full", action="store_true", help="Full diagnosis with benchmarks")
        parser.add_argument("--mock", type=str, metavar="PROFILE", help="Mock mode: healthy/degraded/critical/mixed")
        parser.add_argument("--output", "-o", type=str, help="Output file")
        parser.add_argument("--json", action="store_true", help="Output as JSON")
        parser.add_argument("--no-color", action="store_true", help="Disable colored output")
        parser.add_argument("--target", type=str, help="Remote target: http://host:port or relay://host:port")
        parser.add_argument("--parallel", type=int, default=10, help="Max parallel checks (v4.0)")
    
    def execute(self, args: argparse.Namespace) -> int:
        """执行诊断（Rich美化）"""
        # 更新reporter配置
        if args.no_color:
            self.reporter = RichReporter(no_color=True)
        
        # 获取检测项
        check_ids = list_checks()
        
        if not args.full:
            # 快速模式：排除耗时检测
            slow_checks = {'benchmark_cpu', 'benchmark_disk', 'benchmark_memory'}
            check_ids = [c for c in check_ids if c not in slow_checks]
        
        # 打印开始信息
        print_diagnosis_start("local", len(check_ids))
        
        # 使用进度条执行
        start_time = time.time()
        results = []
        
        with DiagnosisProgress(len(check_ids), "Running checks...") as progress:
            # 分批执行，实时更新进度
            batch_size = 10
            for i in range(0, len(check_ids), batch_size):
                batch = check_ids[i:i+batch_size]
                batch_results = run_checks_parallel(
                    batch,
                    max_concurrent=args.parallel,
                    timeouts=CHECK_TIMEOUTS
                )
                results.extend(batch_results)
                progress.update(len(batch))
                
                # 实时显示结果
                for r in batch_results:
                    if r.get("result"):
                        self.reporter.print_check_result(r["result"].__dict__ if hasattr(r["result"], '__dict__') else r)
        
        elapsed = time.time() - start_time
        
        # 计算统计
        passed = sum(1 for r in results if r.get("result") and getattr(r["result"], 'passed', False))
        warning = sum(1 for r in results if r.get("result") and getattr(r["result"], 'severity', None) and r["result"].severity.value == 'warning')
        critical = sum(1 for r in results if r.get("result") and getattr(r["result"], 'severity', None) and r["result"].severity.value == 'critical')
        score = int((passed / len(results)) * 100) if results else 0
        
        # 打印汇总
        print_diagnosis_complete(elapsed, results)
        
        self.reporter.print_summary_panel({
            "total": len(results),
            "passed": passed,
            "warning": warning,
            "critical": critical,
            "score": score
        })
        
        # JSON输出
        if args.json:
            self._output_json(results, args.output)
        
        # 返回退出码
        if critical > 0:
            return 2
        elif warning > 0:
            return 1
        return 0
    
    def _output_json(self, results: list, output_path: Optional[str]):
        """JSON输出"""
        import json
        data = [{"check_id": r.get("check_id"), 
                "passed": getattr(r.get("result"), 'passed', False),
                "severity": getattr(getattr(r.get("result"), 'severity', None), 'value', 'unknown')}
               for r in results]
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            print(f"\nSaved to: {output_path}")
        else:
            print("\n" + json.dumps(data, indent=2))
