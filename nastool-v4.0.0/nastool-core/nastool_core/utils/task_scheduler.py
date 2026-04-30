"""
Task Scheduler for NASTool

Provides intelligent task scheduling for efficient batch diagnosis.
"""

import asyncio
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class TaskInfo:
    """Task information"""
    device_id: str
    priority: int = 0
    estimated_duration: float = 0.0
    dependencies: List[str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class TaskScheduler:
    """
    Intelligent task scheduler for batch diagnosis.
    
    Features:
    - Priority-based scheduling
    - Dependency management
    - Adaptive concurrency
    - Load balancing
    """
    
    def __init__(self, max_concurrency: int = 4):
        """
        Initialize task scheduler.
        
        Args:
            max_concurrency: Maximum concurrent tasks
        """
        self.max_concurrency = max_concurrency
        self.pending_tasks: List[TaskInfo] = []
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.completed_tasks: List[str] = []
        self.task_results: Dict[str, Any] = {}
    
    def add_task(self, task: TaskInfo):
        """
        Add task to scheduler.
        
        Args:
            task: Task information
        """
        self.pending_tasks.append(task)
    
    def add_tasks(self, tasks: List[TaskInfo]):
        """
        Add multiple tasks to scheduler.
        
        Args:
            tasks: List of task information
        """
        self.pending_tasks.extend(tasks)
    
    def _can_run(self, task: TaskInfo) -> bool:
        """
        Check if task can run (dependencies met).
        
        Args:
            task: Task information
            
        Returns:
            True if task can run
        """
        for dep in task.dependencies:
            if dep not in self.completed_tasks:
                return False
        return True
    
    def _get_next_tasks(self) -> List[TaskInfo]:
        """
        Get next tasks to run based on priority and dependencies.
        
        Returns:
            List of tasks to run
        """
        # Filter tasks that can run
        runnable = [t for t in self.pending_tasks if self._can_run(t)]
        
        # Sort by priority (descending) and estimated duration (ascending)
        runnable.sort(key=lambda x: (-x.priority, x.estimated_duration))
        
        # Calculate available slots
        available = self.max_concurrency - len(self.running_tasks)
        
        return runnable[:available]
    
    async def run(self, task_func, callback=None):
        """
        Run all tasks with intelligent scheduling.
        
        Args:
            task_func: Function to execute for each task
            callback: Optional callback for task completion
            
        Returns:
            Dict of task results
        """
        total_tasks = len(self.pending_tasks)
        completed = 0
        
        while self.pending_tasks or self.running_tasks:
            # Get next tasks to run
            next_tasks = self._get_next_tasks()
            
            # Start new tasks
            for task in next_tasks:
                self.pending_tasks.remove(task)
                
                async def run_task(task_id):
                    try:
                        result = await task_func(task_id)
                        self.task_results[task_id] = result
                        self.completed_tasks.append(task_id)
                        
                        if callback:
                            await callback(task_id, result)
                    except Exception as e:
                        self.task_results[task_id] = {'error': str(e)}
                        self.completed_tasks.append(task_id)
                    finally:
                        if task_id in self.running_tasks:
                            del self.running_tasks[task_id]
                
                task_coro = run_task(task.device_id)
                self.running_tasks[task.device_id] = asyncio.create_task(task_coro)
            
            # Check if any tasks completed
            if self.running_tasks:
                done, _ = await asyncio.wait(
                    self.running_tasks.values(),
                    return_when=asyncio.FIRST_COMPLETED
                )
            else:
                # No tasks running, wait a bit
                await asyncio.sleep(0.1)
            
            # Update progress
            new_completed = len(self.completed_tasks)
            if new_completed > completed:
                completed = new_completed
                if callback and hasattr(callback, 'progress'):
                    callback.progress(completed, total_tasks)
        
        return self.task_results
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get scheduler statistics.
        
        Returns:
            Scheduler statistics
        """
        return {
            'total_tasks': len(self.task_results),
            'completed_tasks': len(self.completed_tasks),
            'pending_tasks': len(self.pending_tasks),
            'running_tasks': len(self.running_tasks)
        }


class AdaptiveTaskScheduler(TaskScheduler):
    """
    Adaptive task scheduler with dynamic concurrency adjustment.
    """
    
    def __init__(self, min_concurrency: int = 2, max_concurrency: int = 8):
        """
        Initialize adaptive scheduler.
        
        Args:
            min_concurrency: Minimum concurrency
            max_concurrency: Maximum concurrency
        """
        super().__init__(max_concurrency)
        self.min_concurrency = min_concurrency
        self.current_concurrency = max_concurrency
        self.execution_times: List[float] = []
    
    def _adjust_concurrency(self):
        """
        Adjust concurrency based on execution times.
        """
        if len(self.execution_times) < 3:
            return
        
        avg_time = sum(self.execution_times[-3:]) / 3
        
        # Adjust concurrency based on average execution time
        if avg_time > 10.0:
            # Slow tasks, reduce concurrency
            self.current_concurrency = max(self.min_concurrency, self.current_concurrency - 1)
        elif avg_time < 2.0:
            # Fast tasks, increase concurrency
            self.current_concurrency = min(self.max_concurrency, self.current_concurrency + 1)
    
    async def run(self, task_func, callback=None):
        """
        Run tasks with adaptive concurrency.
        """
        start_time = time.time()
        result = await super().run(task_func, callback)
        execution_time = time.time() - start_time
        
        self.execution_times.append(execution_time)
        self._adjust_concurrency()
        
        return result
