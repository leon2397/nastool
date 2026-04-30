"""
Error Handler for NASTool

Provides robust error handling and exception recovery mechanisms.
"""

import traceback
import sys
import time
from typing import Optional, Callable, Dict, Any, List, Type
from dataclasses import dataclass


@dataclass
class ErrorInfo:
    """
    Error information structure
    """
    error_type: str
    message: str
    details: Dict[str, Any]
    timestamp: float
    traceback: Optional[str] = None


class ErrorHandler:
    """
    Centralized error handler for NASTool.
    
    Features:
    - Exception catching and logging
    - Retry mechanism
    - Graceful degradation
    - Error classification
    """
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        """
        Initialize error handler.
        
        Args:
            max_retries: Maximum number of retries
            retry_delay: Delay between retries in seconds
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.error_history: List[ErrorInfo] = []
    
    def catch(self, func: Callable, *args, **kwargs) -> Any:
        """
        Catch and handle exceptions from a function.
        
        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Function result or None if failed
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_info = self._create_error_info(e)
            self._log_error(error_info)
            self.error_history.append(error_info)
            return None
    
    def retry(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with retry mechanism.
        
        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Function result or None if all retries failed
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    self._log_retry(attempt, e)
                    time.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
                else:
                    error_info = self._create_error_info(e)
                    self._log_error(error_info)
                    self.error_history.append(error_info)
        
        return None
    
    def classify_error(self, error: Exception) -> str:
        """
        Classify error type.
        
        Args:
            error: Exception to classify
            
        Returns:
            Error category
        """
        error_types = {
            "network": [ConnectionError, TimeoutError, OSError],
            "permission": [PermissionError, FileNotFoundError],
            "configuration": [ValueError, KeyError, TypeError],
            "resource": [MemoryError, OSError],
            "external": [ImportError, ModuleNotFoundError],
            "unknown": [Exception]
        }
        
        for category, error_classes in error_types.items():
            for error_class in error_classes:
                if isinstance(error, error_class):
                    return category
        
        return "unknown"
    
    def _create_error_info(self, error: Exception) -> ErrorInfo:
        """
        Create error information from exception.
        """
        error_type = self.classify_error(error)
        message = str(error)
        
        details = {
            "error_class": error.__class__.__name__,
            "category": error_type,
            "args": str(error.args),
        }
        
        tb = traceback.format_exc() if error_type != "network" else None
        
        return ErrorInfo(
            error_type=error_type,
            message=message,
            details=details,
            timestamp=time.time(),
            traceback=tb
        )
    
    def _log_error(self, error_info: ErrorInfo):
        """
        Log error information.
        """
        from nastool_common.logger import get_logger
        logger = get_logger(__name__)
        
        log_message = f"[{error_info.error_type.upper()}] {error_info.message}"
        
        if error_info.traceback:
            logger.error(log_message)
            logger.debug(error_info.traceback)
        else:
            logger.warning(log_message)
    
    def _log_retry(self, attempt: int, error: Exception):
        """
        Log retry attempt.
        """
        from nastool_common.logger import get_logger
        logger = get_logger(__name__)
        
        logger.info(f"Retry {attempt + 1}/{self.max_retries} after error: {error}")
    
    def get_error_history(self) -> List[ErrorInfo]:
        """
        Get error history.
        
        Returns:
            List of error information
        """
        return self.error_history
    
    def clear_error_history(self):
        """
        Clear error history.
        """
        self.error_history.clear()
    
    def get_error_statistics(self) -> Dict[str, int]:
        """
        Get error statistics.
        
        Returns:
            Error counts by category
        """
        stats = {}
        for error in self.error_history:
            stats[error.error_type] = stats.get(error.error_type, 0) + 1
        return stats


def safe_execute(func: Callable, *args, **kwargs) -> Any:
    """
    Safe execute function with error handling.
    
    Args:
        func: Function to execute
        *args: Positional arguments
        **kwargs: Keyword arguments
        
    Returns:
        Function result or None if failed
    """
    handler = ErrorHandler()
    return handler.catch(func, *args, **kwargs)


def retry_execute(func: Callable, *args, **kwargs) -> Any:
    """
    Execute function with retry mechanism.
    
    Args:
        func: Function to execute
        *args: Positional arguments
        **kwargs: Keyword arguments
        
    Returns:
        Function result or None if all retries failed
    """
    handler = ErrorHandler()
    return handler.retry(func, *args, **kwargs)


def handle_network_errors(func: Callable) -> Callable:
    """
    Decorator for handling network errors.
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function
    """
    def wrapper(*args, **kwargs):
        handler = ErrorHandler(max_retries=3, retry_delay=2.0)
        return handler.retry(func, *args, **kwargs)
    return wrapper


def handle_config_errors(func: Callable) -> Callable:
    """
    Decorator for handling configuration errors.
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function
    """
    def wrapper(*args, **kwargs):
        handler = ErrorHandler(max_retries=1, retry_delay=0.5)
        return handler.catch(func, *args, **kwargs)
    return wrapper
