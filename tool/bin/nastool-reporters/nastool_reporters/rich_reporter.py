"""
rich_reporter.py - Rich库美化输出

提供表格、进度条、面板等美化输出。
"""

from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.syntax import Syntax
from rich import box

from nastool_common.logger import get_logger

logger = get_logger(__name__)

# 全局console
console = Console()


class RichReporter:
    """Rich美化报告输出"""
    
    def __init__(self, no_color: bool = False):
        self.console = Console(no_color=no_color)
        
    def print_header(self, title: str, subtitle: str = ""):
        """打印标题头"""
        self.console.print()
        self.console.print(Panel(
            f"[bold blue]{title}[/bold blue]\n[cyan]{subtitle}[/cyan]",
            box=box.ROUNDED,
            border_style="blue"
        ))
        
    def print_device_table(self, devices: List[Dict[str, Any]]):
        """打印设备列表表格"""
        table = Table(
            title="Device List",
            box=box.SIMPLE_HEAD,
            header_style="bold magenta"
        )
        
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Host", style="green")
        table.add_column("Type", style="yellow")
        table.add_column("Group", style="blue")
        table.add_column("Status", justify="center")
        
        for d in devices:
            status = d.get("status", "unknown")
            if status == "online":
                status_text = "[green]● online[/green]"
            elif status == "offline":
                status_text = "[red]● offline[/red]"
            else:
                status_text = "[yellow]● unknown[/yellow]"
            
            table.add_row(
                d.get("id", "-"),
                d.get("host", "-"),
                d.get("type", "-"),
                d.get("group", "-"),
                status_text
            )
        
        self.console.print(table)
        
    def print_check_result(self, result: Dict[str, Any]):
        """打印单个检测结果"""
        severity = result.get("severity", "info")
        check_id = result.get("check_id", "unknown")
        message = result.get("message", "")
        
        # 根据严重级别选择颜色
        colors = {
            "critical": "red",
            "warning": "yellow",
            "info": "blue",
            "passed": "green"
        }
        color = colors.get(severity, "white")
        
        icon = "✓" if severity == "passed" else "✗" if severity == "critical" else "!"
        
        self.console.print(f"[{color}]{icon} {check_id:<40} {message}[/{color}]")
        
    def print_summary_panel(self, stats: Dict[str, Any]):
        """打印汇总面板"""
        total = stats.get("total", 0)
        passed = stats.get("passed", 0)
        warning = stats.get("warning", 0)
        critical = stats.get("critical", 0)
        score = stats.get("score", 0)
        
        # 根据分数选择颜色
        if score >= 90:
            score_color = "green"
        elif score >= 70:
            score_color = "yellow"
        else:
            score_color = "red"
        
        content = f"""
[bold]Total Checks:[/bold]    {total}
[green]Passed:[/green]          {passed}
[yellow]Warning:[/yellow]        {warning}
[red]Critical:[/red]        {critical}

[bold {score_color}]Overall Score: {score}/100[/bold {score_color}]
        """.strip()
        
        self.console.print(Panel(
            content,
            title="Diagnosis Summary",
            box=box.ROUNDED,
            border_style=score_color
        ))
        
    def create_progress(self) -> Progress:
        """创建进度条"""
        return Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=40),
            TaskProgressColumn(),
            console=self.console
        )


class DiagnosisProgress:
    """诊断进度显示"""
    
    def __init__(self, total_checks: int, description: str = "Diagnosing"):
        self.total = total_checks
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=40),
            TaskProgressColumn(),
            console=Console()
        )
        self.task = self.progress.add_task(description, total=total_checks)
        
    def __enter__(self):
        self.progress.start()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.progress.stop()
        
    def update(self, advance: int = 1):
        """更新进度"""
        self.progress.update(self.task, advance=advance)
        
    def set_description(self, description: str):
        """设置描述"""
        self.progress.update(self.task, description=description)


def print_diagnosis_start(device_id: str, check_count: int):
    """打印诊断开始信息"""
    console.print()
    console.print(Panel(
        f"[bold]Device:[/bold] {device_id}\n"
        f"[bold]Checks:[/bold] {check_count}",
        title="[bold blue]Starting Diagnosis[/bold blue]",
        box=box.ROUNDED
    ))
    

def print_diagnosis_complete(duration: float, results: List[Dict]):
    """打印诊断完成信息"""
    passed = sum(1 for r in results if r.get("passed"))
    total = len(results)
    
    console.print()
    console.print(Panel(
        f"[green]Completed in {duration:.2f}s[/green]\n"
        f"{passed}/{total} checks passed",
        title="[bold green]Diagnosis Complete[/bold green]",
        box=box.ROUNDED
    ))


# 便捷函数
def print_error(message: str):
    """打印错误信息"""
    console.print(f"[bold red]Error:[/bold red] {message}")
    

def print_warning(message: str):
    """打印警告信息"""
    console.print(f"[bold yellow]Warning:[/bold yellow] {message}")
    

def print_success(message: str):
    """打印成功信息"""
    console.print(f"[bold green]Success:[/bold green] {message}")
    

def print_info(message: str):
    """打印信息"""
    console.print(f"[cyan]Info:[/cyan] {message}")
