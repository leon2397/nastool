"""
Network Resilience Utilities for NASTool

Provides robust network error handling and resilience mechanisms.
"""

import socket
import time
import urllib.request
import urllib.error
from typing import Optional, Callable, Dict, Any, List, Tuple
from dataclasses import dataclass


@dataclass
class NetworkStatus:
    """
    Network status information
    """
    connected: bool
    latency: float
    errors: List[str]
    timestamp: float


class NetworkResilience:
    """
    Network resilience manager for NASTool.
    
    Features:
    - Network connectivity checking
    - Smart retry with exponential backoff
    - Network status monitoring
    - Failover mechanisms
    """
    
    def __init__(self, timeout: int = 10, max_retries: int = 3):
        """
        Initialize network resilience manager.
        
        Args:
            timeout: Network timeout in seconds
            max_retries: Maximum number of retries
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.status_history: List[NetworkStatus] = []
    
    def check_connectivity(self, host: str = "8.8.8.8", port: int = 53) -> NetworkStatus:
        """
        Check network connectivity.
        
        Args:
            host: Host to check
            port: Port to check
            
        Returns:
            Network status
        """
        errors = []
        connected = False
        latency = 0.0
        
        try:
            start_time = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((host, port))
            sock.close()
            latency = (time.time() - start_time) * 1000  # ms
            connected = True
        except socket.timeout:
            errors.append(f"Connection timeout to {host}:{port}")
        except socket.error as e:
            errors.append(f"Connection error: {e}")
        
        status = NetworkStatus(
            connected=connected,
            latency=latency,
            errors=errors,
            timestamp=time.time()
        )
        
        self.status_history.append(status)
        return status
    
    def is_connected(self) -> bool:
        """
        Check if network is connected.
        
        Returns:
            True if connected
        """
        status = self.check_connectivity()
        return status.connected
    
    def retry_with_backoff(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute network operation with retry and backoff.
        
        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Function result or None if failed
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    # Exponential backoff
                    delay = (2 ** attempt) * 1
                    time.sleep(delay)
                else:
                    return None
        
        return None
    
    def fetch_url(self, url: str, timeout: Optional[int] = None) -> Optional[str]:
        """
        Fetch URL with retry and error handling.
        
        Args:
            url: URL to fetch
            timeout: Timeout in seconds
            
        Returns:
            Response content or None
        """
        timeout = timeout or self.timeout
        
        def _fetch():
            req = urllib.request.Request(url, headers={
                'User-Agent': 'NASTool/4.0'
            })
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read().decode('utf-8')
        
        return self.retry_with_backoff(_fetch)
    
    def get_network_info(self) -> Dict[str, Any]:
        """
        Get network information.
        
        Returns:
            Network information
        """
        info = {
            "status": self.check_connectivity(),
            "history": self.status_history[-5:] if self.status_history else [],
            "timeout": self.timeout,
            "max_retries": self.max_retries
        }
        return info
    
    def detect_network_issues(self) -> List[str]:
        """
        Detect network issues from history.
        
        Returns:
            List of detected issues
        """
        issues = []
        
        if not self.status_history:
            return issues
        
        # Check recent status
        recent_status = self.status_history[-5:]
        failed_attempts = sum(1 for s in recent_status if not s.connected)
        
        if failed_attempts >= 3:
            issues.append("Persistent network connectivity issues detected")
        
        # Check latency
        latencies = [s.latency for s in recent_status if s.connected]
        if latencies:
            avg_latency = sum(latencies) / len(latencies)
            if avg_latency > 200:
                issues.append(f"High network latency detected: {avg_latency:.1f}ms")
        
        return issues
    
    def clear_history(self):
        """
        Clear status history.
        """
        self.status_history.clear()


class NetworkFallback:
    """
    Network fallback manager for handling network failures.
    """
    
    def __init__(self, primary_hosts: List[str], fallback_hosts: List[str]):
        """
        Initialize network fallback manager.
        
        Args:
            primary_hosts: Primary hosts
            fallback_hosts: Fallback hosts
        """
        self.primary_hosts = primary_hosts
        self.fallback_hosts = fallback_hosts
        self.current_hosts = primary_hosts.copy()
        self.resilience = NetworkResilience()
    
    def get_available_host(self) -> Optional[str]:
        """
        Get available host.
        
        Returns:
            Available host or None
        """
        # Check primary hosts first
        for host in self.current_hosts:
            status = self.resilience.check_connectivity(host.split(':')[0])
            if status.connected:
                return host
        
        # Try fallback hosts if primary fail
        for host in self.fallback_hosts:
            status = self.resilience.check_connectivity(host.split(':')[0])
            if status.connected:
                return host
        
        return None
    
    def switch_to_fallback(self):
        """
        Switch to fallback hosts.
        """
        self.current_hosts = self.fallback_hosts.copy()
    
    def switch_to_primary(self):
        """
        Switch back to primary hosts.
        """
        self.current_hosts = self.primary_hosts.copy()


def is_port_open(host: str, port: int, timeout: int = 5) -> bool:
    """
    Check if port is open.
    
    Args:
        host: Host to check
        port: Port to check
        timeout: Timeout in seconds
        
    Returns:
        True if port is open
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False

def get_local_ip() -> Optional[str]:
    """
    Get local IP address.
    
    Returns:
        Local IP address or None
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(('8.8.8.8', 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except:
        return None

def calculate_network_score() -> int:
    """
    Calculate network health score (0-100).
    
    Returns:
        Network health score
    """
    resilience = NetworkResilience()
    status = resilience.check_connectivity()
    
    if not status.connected:
        return 0
    
    # Base score
    score = 100
    
    # Deduct for latency
    if status.latency > 100:
        score -= min(50, int(status.latency / 2))
    
    # Check additional endpoints
    endpoints = ["google.com", "cloudflare.com", "github.com"]
    reachable = 0
    
    for endpoint in endpoints:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            sock.connect((endpoint, 80))
            sock.close()
            reachable += 1
        except:
            pass
    
    # Adjust score based on reachability
    if reachable < len(endpoints):
        score -= (len(endpoints) - reachable) * 10
    
    return max(0, min(100, score))
