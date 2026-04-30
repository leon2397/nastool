"""
Network Utilities with Timeout for nastool

Provides network operations with built-in timeout protection.

Usage:
    from utils.network_timeout import safe_request, check_url

    # Safe HTTP request with timeout
    response = safe_request('GET', 'https://example.com')

    # Check URL availability
    is_up = check_url('https://example.com', timeout=5)
"""

import socket
from typing import Optional, Dict, Any
from nastool_common.logger import get_logger

logger = get_logger(__name__)

# Default timeouts
DEFAULT_TIMEOUT = 10  # seconds
CONNECT_TIMEOUT = 5  # seconds
READ_TIMEOUT = 30  # seconds


def safe_request(method: str, url: str, timeout: int = DEFAULT_TIMEOUT, **kwargs) -> Optional[Any]:
    """
    Make a safe HTTP request with timeout.

    Args:
        method: HTTP method (GET, POST, etc.)
        url: Request URL
        timeout: Request timeout in seconds
        **kwargs: Additional arguments for requests

    Returns:
        Response object or None if failed
    """
    try:
        from requests import request
    except ImportError:
        logger.error("requests not installed - HTTP requests disabled")
        return None

    try:
        # Set timeout if not provided
        if "timeout" not in kwargs:
            kwargs["timeout"] = timeout

        response = request(method, url, **kwargs)
        return response

    except Exception as e:
        logger.error(f"Request failed: {method} {url} - {e}")
        return None


def check_url(url: str, timeout: int = CONNECT_TIMEOUT) -> bool:
    """
    Check if URL is reachable.

    Args:
        url: URL to check
        timeout: Connection timeout in seconds

    Returns:
        True if reachable, False otherwise
    """
    try:
        response = safe_request("HEAD", url, timeout=timeout, allow_redirects=True)
        return response is not None and response.status_code < 500
    except Exception as e:
        return False


def check_port(host: str, port: int, timeout: int = 3) -> bool:
    """
    Check if a port is open.

    Args:
        host: Host to check
        port: Port number
        timeout: Connection timeout in seconds

    Returns:
        True if port is open, False otherwise
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        logger.debug(f"Port check failed: {host}:{port} - {e}")
        return False


def get_local_ip() -> Optional[str]:
    """
    Get local IP address.

    Returns:
        Local IP address or None if unavailable
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        local_ip = sock.getsockname()[0]
        sock.close()
        return local_ip
    except Exception as e:
        logger.debug(f"Failed to get local IP: {e}")
        return None


def resolve_hostname(hostname: str, timeout: int = 5) -> Optional[str]:
    """
    Resolve hostname to IP address.

    Args:
        hostname: Hostname to resolve
        timeout: DNS lookup timeout in seconds

    Returns:
        IP address or None if failed
    """
    try:
        import signal

        def timeout_handler(signum, frame):
            raise TimeoutError("DNS lookup timed out")

        # Set timeout alarm (Unix only)
        if hasattr(signal, "SIGALRM"):
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout)

        try:
            ip = socket.gethostbyname(hostname)
            return ip
        finally:
            if hasattr(signal, "SIGALRM"):
                signal.alarm(0)

    except Exception as e:
        logger.debug(f"Failed to resolve {hostname}: {e}")
        return None


def download_file(
    url: str, dest_path: str, timeout: int = READ_TIMEOUT, chunk_size: int = 8192
) -> bool:
    """
    Download a file with timeout protection.

    Args:
        url: Download URL
        dest_path: Destination file path
        timeout: Download timeout in seconds
        chunk_size: Download chunk size

    Returns:
        True if successful, False otherwise
    """
    try:
        response = safe_request("GET", url, timeout=timeout, stream=True)

        if response is None or response.status_code != 200:
            logger.error(f"Download failed: {url}")
            return False

        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)

        logger.info(f"Downloaded: {url} -> {dest_path}")
        return True

    except Exception as e:
        logger.error(f"Download failed: {url} - {e}")
        return False


if __name__ == "__main__":
    # Test network utilities
    print("=" * 50)
    print("Network Utilities Test")
    print("=" * 50)
    print()

    print("Local IP:", get_local_ip() or "unavailable")
    print()

    print("Checking ports:")
    for port in [80, 443, 22]:
        is_open = check_port("localhost", port, timeout=1)
        status = "open" if is_open else "closed"
        print(f"  localhost:{port} - {status}")

    print()
    print("Checking URLs:")
    for url in ["https://www.baidu.com", "https://www.google.com"]:
        is_up = check_url(url, timeout=5)
        status = "reachable" if is_up else "unreachable"
        print(f"  {url} - {status}")
