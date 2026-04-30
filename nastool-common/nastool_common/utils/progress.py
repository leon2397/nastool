#!/usr/bin/env python3
"""
进度可视化模块 - 提供美观的进度条显示
"""

import sys
import time
from typing import Optional

class ProgressBar:
    """进度条类"""
    
    def __init__(self, total: int = 100, width: int = 50, show_percent: bool = True, show_time: bool = True):
        self.total = total
        self.width = width
        self.show_percent = show_percent
        self.show_time = show_time
        self.current = 0
        self.start_time = time.time()
        self.last_update_time = time.time()
    
    def update(self, current: int = None, status: str = ""):
        """更新进度"""
        if current is not None:
            self.current = min(current, self.total)
        else:
            self.current = min(self.current + 1, self.total)
        
        self._render(status)
    
    def _render(self, status: str = ""):
        """渲染进度条"""
        percent = (self.current / self.total) * 100
        filled = int(self.width * percent / 100)
        remaining = self.width - filled
        
        # 构建进度条
        bar = "["
        bar += "█" * filled
        bar += "░" * remaining
        bar += "]"
        
        # 构建输出字符串
        output = f"\r{bar}"
        
        # 添加百分比
        if self.show_percent:
            output += f" {percent:6.1f}%"
        
        # 添加状态
        if status:
            output += f" - {status}"
        
        # 添加时间信息
        if self.show_time:
            elapsed = time.time() - self.start_time
            if self.current > 0:
                eta = (elapsed / self.current) * (self.total - self.current)
                output += f" (已用: {self._format_time(elapsed)}, 剩余: {self._format_time(eta)})"
            else:
                output += f" (已用: {self._format_time(elapsed)})"
        
        # 输出
        sys.stdout.write(output)
        sys.stdout.flush()
        
        # 如果完成，换行
        if self.current >= self.total:
            sys.stdout.write("\n")
            sys.stdout.flush()
    
    def _format_time(self, seconds: float) -> str:
        """格式化时间"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m{secs}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            return f"{hours}h{minutes}m{secs}s"
    
    def finish(self, status: str = "完成"):
        """完成进度条"""
        self.current = self.total
        self._render(status)

class Spinner:
    """旋转指示器"""
    
    def __init__(self, message: str = "", delay: float = 0.1):
        self.message = message
        self.delay = delay
        self.spinner_chars = ['|', '/', '-', '\\']
        self.current_char = 0
        self.running = False
        self.thread = None
    
    def start(self):
        """开始旋转"""
        self.running = True
        while self.running:
            sys.stdout.write(f"\r{self.spinner_chars[self.current_char]} {self.message}")
            sys.stdout.flush()
            self.current_char = (self.current_char + 1) % len(self.spinner_chars)
            time.sleep(self.delay)
    
    def stop(self):
        """停止旋转"""
        self.running = False
        # 清除旋转器
        sys.stdout.write("\r" + " " * (len(self.message) + 2) + "\r")
        sys.stdout.flush()

class StatusIndicator:
    """状态指示器"""
    
    def __init__(self):
        self.statuses = []
    
    def add_status(self, name: str, status: str = "pending"):
        """添加状态项"""
        self.statuses.append({
            'name': name,
            'status': status,
            'start_time': time.time()
        })
    
    def update_status(self, name: str, status: str):
        """更新状态"""
        for s in self.statuses:
            if s['name'] == name:
                s['status'] = status
                s['end_time'] = time.time()
                break
    
    def print_status(self):
        """打印所有状态"""
        max_name_length = max(len(s['name']) for s in self.statuses)
        
        print("\n📋 检测状态:")
        for s in self.statuses:
            status_icon = self._get_status_icon(s['status'])
            duration = self._get_duration(s)
            print(f"   {status_icon} {s['name'].ljust(max_name_length)} {duration}")
    
    def _get_status_icon(self, status: str) -> str:
        """获取状态图标"""
        icons = {
            'pending': '◯',
            'in_progress': '◉',
            'completed': '✓',
            'success': '✓',
            'error': '✗',
            'warning': '⚠'
        }
        return icons.get(status, '◯')
    
    def _get_duration(self, status: dict) -> str:
        """获取耗时"""
        if 'end_time' in status and 'start_time' in status:
            duration = status['end_time'] - status['start_time']
            return f"({duration:.2f}s)"
        return ""

class CheckStatus:
    """检查状态枚举类"""
    PENDING = 'pending'
    RUNNING = 'running'
    PASSED = 'passed'
    FAILED = 'failed'
    WARNING = 'warning'

class ProgressTracker:
    """进度跟踪器 - 兼容原有API"""
    
    def __init__(self, total_items: int = 0):
        self.total = total_items
        self.completed = 0
        self.current_item = ""
        self._start_time = time.time()
    
    def start_item(self, name: str):
        """开始一个新的检查项"""
        self.current_item = name
    
    def complete_item(self):
        """完成当前检查项"""
        self.completed += 1
    
    def get_progress(self) -> float:
        """获取当前进度百分比"""
        if self.total == 0:
            return 0.0
        return (self.completed / self.total) * 100
    
    def get_elapsed(self) -> float:
        """获取已耗时"""
        return time.time() - self._start_time

def create_tracker(total: int = 100) -> ProgressTracker:
    """创建进度跟踪器"""
    return ProgressTracker(total_items=total)

class ProgressManager:
    """进度管理器"""
    
    def __init__(self, tasks: list = None):
        self.tasks = tasks or []
        self.current_task = 0
        self.progress_bar = ProgressBar(total=len(tasks)) if tasks else None
        self.status_indicator = StatusIndicator()
        
        # 初始化状态指示器
        for task in self.tasks:
            self.status_indicator.add_status(task, 'pending')
    
    def start_task(self, task_name: str = None):
        """开始任务"""
        if task_name:
            # 找到任务索引
            try:
                idx = next(i for i, t in enumerate(self.tasks) if t == task_name)
                self.current_task = idx
            except StopIteration:
                pass
        
        if self.current_task < len(self.tasks):
            task = self.tasks[self.current_task]
            self.status_indicator.update_status(task, 'in_progress')
            print(f"\n🔍 {task}...")
            
            if self.progress_bar:
                self.progress_bar.update(self.current_task, task)
    
    def complete_task(self, success: bool = True, message: str = ""):
        """完成任务"""
        if self.current_task < len(self.tasks):
            task = self.tasks[self.current_task]
            status = 'success' if success else 'error'
            self.status_indicator.update_status(task, status)
            
            if message:
                print(f"   {'✅' if success else '❌'} {message}")
            else:
                print(f"   {'✅' if success else '❌'} 完成")
            
            if self.progress_bar:
                self.progress_bar.update(self.current_task + 1, task)
            
            self.current_task += 1
    
    def finish(self):
        """完成所有任务"""
        if self.progress_bar:
            self.progress_bar.finish("全部完成")
        
        self.status_indicator.print_status()

def example():
    """示例用法"""
    print("📊 进度条示例:")
    pb = ProgressBar(total=10)
    for i in range(10):
        pb.update(i + 1, f"处理项目 {i + 1}")
        time.sleep(0.3)
    
    print("\n📋 状态指示器示例:")
    tasks = ["网络诊断", "硬件检测", "依赖检查", "系统分析"]
    pm = ProgressManager(tasks)
    
    for task in tasks:
        pm.start_task(task)
        time.sleep(0.5)
        pm.complete_task(success=True)
    
    pm.finish()

if __name__ == "__main__":
    example()
