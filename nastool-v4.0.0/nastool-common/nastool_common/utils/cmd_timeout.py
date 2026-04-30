"""
Command Execution with Timeout for nastool

Provides subprocess execution with built-in timeout protection.

Usage:
    from utils.cmd_timeout import run_cmd, run_cmd_safe

    # Run command with timeout
    result = run_cmd(['ls', '-la'], timeout=30)

    # Safe run that never raises
    result = run_cmd_safe(['ls', '-la'], timeout=30)
"""

import subprocess
import shlex
from typing import Optional, List, Tuple, Union
from dataclasses import dataclass
from nastool_common.logger import get_logger

logger = get_logger(__name__)

# Default timeouts
DEFAULT_TIMEOUT = 30  # seconds
SHORT_TIMEOUT = 10  # seconds
LONG_TIMEOUT = 60  # seconds


@dataclass
class CommandResult:
    """Result of command execution"""

    success: bool
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False
    exception: Optional[str] = None


def run_cmd(
    cmd: Union[str, List[str]],
    timeout: int = DEFAULT_TIMEOUT,
    cwd: str = None,
    env: dict = None,
    shell: bool = False,
    check: bool = True,
) -> CommandResult:
    """
    Run a command with timeout protection.

    Args:
        cmd: Command to run (string or list)
        timeout: Command timeout in seconds
        cwd: Working directory
        env: Environment variables
        shell: Run in shell
        check: Raise on non-zero exit

    Returns:
        CommandResult with output and status

    Raises:
        subprocess.TimeoutExpired: If command times out
        subprocess.CalledProcessError: If check=True and command fails
    """
    # Convert string to list if needed
    if isinstance(cmd, str) and not shell:
        cmd = shlex.split(cmd)

    logger.debug(f"Running: {cmd if isinstance(cmd, str) else ' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            env=env,
            shell=shell,
            check=check,
        )

        return CommandResult(
            success=True, returncode=result.returncode, stdout=result.stdout, stderr=result.stderr
        )

    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out after {timeout}s: {cmd}")
        raise

    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with code {e.returncode}: {cmd}")
        raise


def run_cmd_safe(
    cmd: Union[str, List[str]],
    timeout: int = DEFAULT_TIMEOUT,
    cwd: str = None,
    env: dict = None,
    shell: bool = False,
) -> CommandResult:
    """
    Run a command safely with timeout protection.

    Never raises exceptions - always returns CommandResult.

    Args:
        cmd: Command to run (string or list)
        timeout: Command timeout in seconds
        cwd: Working directory
        env: Environment variables
        shell: Run in shell

    Returns:
        CommandResult with output and status
    """
    # Convert string to list if needed
    if isinstance(cmd, str) and not shell:
        cmd = shlex.split(cmd)

    logger.debug(f"Running (safe): {cmd if isinstance(cmd, str) else ' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            env=env,
            shell=shell,
            check=False,
        )

        return CommandResult(
            success=result.returncode == 0,
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )

    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out after {timeout}s: {cmd}")
        return CommandResult(
            success=False,
            returncode=-1,
            stdout="",
            stderr=f"Command timed out after {timeout} seconds",
            timed_out=True,
        )

    except Exception as e:
        logger.error(f"Command failed: {cmd} - {e}")
        return CommandResult(
            success=False, returncode=-1, stdout="", stderr=str(e), exception=str(e)
        )


def run_cmd_background(
    cmd: Union[str, List[str]], cwd: str = None, env: dict = None
) -> subprocess.Popen:
    """
    Run a command in the background.

    Args:
        cmd: Command to run (string or list)
        cwd: Working directory
        env: Environment variables

    Returns:
        Popen object for the background process
    """
    # Convert string to list if needed
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)

    logger.debug(f"Running (background): {' '.join(cmd)}")

    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd, env=env)


def check_cmd_available(cmd: str) -> bool:
    """
    Check if a command is available in PATH.

    Args:
        cmd: Command name

    Returns:
        True if available, False otherwise
    """
    import shutil

    return shutil.which(cmd) is not None


def get_cmd_output(cmd: Union[str, List[str]], timeout: int = DEFAULT_TIMEOUT) -> Optional[str]:
    """
    Get command output as string.

    Args:
        cmd: Command to run
        timeout: Command timeout in seconds

    Returns:
        Command stdout or None if failed
    """
    result = run_cmd_safe(cmd, timeout=timeout)
    return result.stdout.strip() if result.success else None


if __name__ == "__main__":
    # Test command utilities
    print("=" * 50)
    print("Command Utilities Test")
    print("=" * 50)
    print()

    print("Testing run_cmd_safe:")

    # Test successful command
    result = run_cmd_safe(["echo", "Hello, World!"])
    print(f"  echo 'Hello, World!'")
    print(f"    success: {result.success}")
    print(f"    stdout: {result.stdout.strip()}")
    print()

    # Test failed command
    result = run_cmd_safe(["ls", "/nonexistent"])
    print(f"  ls /nonexistent")
    print(f"    success: {result.success}")
    print(f"    stderr: {result.stderr.strip()[:50]}...")
    print()

    # Test timeout
    import platform

    if platform.system() != "Windows":
        result = run_cmd_safe(["sleep", "5"], timeout=1)
        print(f"  sleep 5 (timeout=1s)")
        print(f"    timed_out: {result.timed_out}")
        print()

    print("Available commands:")
    for cmd in ["python3", "pip3", "git", "docker"]:
        available = check_cmd_available(cmd)
        status = "available" if available else "not found"
        print(f"  {cmd}: {status}")
