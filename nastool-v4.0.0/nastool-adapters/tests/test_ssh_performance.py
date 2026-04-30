# -*- coding: utf-8 -*-
"""Test SSH performance optimization for nastool-adapters"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_ssh_detector_batch_execution():
    """Test SSH batch command execution"""
    from unittest.mock import MagicMock, patch
    from nastool_adapters.ssh_detector import RemoteSSHDetector

    detector = RemoteSSHDetector("192.168.1.100", username="admin", password="password")
    detector._connected = True

    mock_client = MagicMock()
    mock_stdout = MagicMock()
    mock_stderr = MagicMock()
    mock_channel = MagicMock()

    mock_stdout.read.return_value.decode.return_value = "test_output"
    mock_stderr.read.return_value.decode.return_value = ""
    mock_stdout.channel.recv_exit_status.return_value = 0
    mock_channel.recv_exit_status.return_value = 0

    mock_client.exec_command.return_value = (MagicMock(), mock_stdout, mock_stderr)
    mock_client.get_transport.return_value = MagicMock()

    with patch.object(detector, '_get_ssh_client', return_value=mock_client):
        commands = ["hostname", "uptime", "df -h", "free -m"]
        results = detector.execute_batch(commands)

        assert len(results) == len(commands)
        assert all(r[0] in commands for r in results)

    detector.disconnect()


def test_ssh_detector_context_manager():
    """Test SSH detector context manager"""
    from unittest.mock import MagicMock, patch
    from nastool_adapters.ssh_detector import RemoteSSHDetector

    with patch('paramiko.SSHClient') as mock_ssh:
        mock_client = MagicMock()
        mock_ssh.return_value = mock_client

        with RemoteSSHDetector("192.168.1.100", username="admin", password="password") as detector:
            mock_client.connect.return_value = None
            detector.connect(use_retry=False)

        mock_client.close.assert_called_once()


def test_ssh_detector_is_connected():
    """Test SSH detector connection status check"""
    from unittest.mock import MagicMock, patch
    from nastool_adapters.ssh_detector import RemoteSSHDetector

    detector = RemoteSSHDetector("192.168.1.100", username="admin", password="password")

    assert not detector.is_connected()

    detector._connected = True
    detector._client = MagicMock()

    mock_transport = MagicMock()
    mock_transport.is_active.return_value = True
    detector._client.get_transport.return_value = mock_transport

    assert detector.is_connected()

    mock_transport.is_active.return_value = False
    assert not detector.is_connected()


def test_ssh_detector_command_timeout():
    """Test SSH detector command timeout parameter"""
    from nastool_adapters.ssh_detector import RemoteSSHDetector

    detector = RemoteSSHDetector(
        "192.168.1.100",
        username="admin",
        password="password",
        command_timeout=20
    )

    assert detector.command_timeout == 20


def test_ssh_detector_optimized_get_device_info():
    """Test SSH detector optimized get_device_info with batch execution"""
    from unittest.mock import MagicMock, patch
    from nastool_adapters.ssh_detector import RemoteSSHDetector

    detector = RemoteSSHDetector("192.168.1.100", username="admin", password="password")
    detector._connected = True

    mock_client = MagicMock()
    mock_transport = MagicMock()
    mock_transport.is_active.return_value = True
    mock_client.get_transport.return_value = mock_transport

    def exec_command_side_effect(command, timeout=None, get_pty=None):
        mock_stdout = MagicMock()
        mock_stderr = MagicMock()
        mock_channel = MagicMock()

        mock_channel.recv_exit_status.return_value = 0

        if "hostname" in command:
            mock_stdout.read.return_value.decode.return_value = "testhost"
        elif "cpuinfo" in command:
            mock_stdout.read.return_value.decode.return_value = "model name\t: Intel Core i7"
        elif "nproc" in command:
            mock_stdout.read.return_value.decode.return_value = "8"
        elif "free -m" in command:
            mock_stdout.read.return_value.decode.return_value = "Mem: 16000 8000 8000"
        elif "uname" in command:
            mock_stdout.read.return_value.decode.return_value = "Linux testhost 5.4.0 x86_64 GNU/Linux"
        else:
            mock_stdout.read.return_value.decode.return_value = ""

        mock_stderr.read.return_value.decode.return_value = ""

        return (MagicMock(), mock_stdout, mock_stderr)

    mock_client.exec_command.side_effect = exec_command_side_effect

    with patch.object(detector, '_get_ssh_client', return_value=mock_client):
        device_info = detector.get_device_info(use_batch=True)

        assert device_info is not None
        assert device_info.hostname == "testhost"
        assert device_info.cpu_cores == 8
        assert device_info.memory_total == 16000

    detector.disconnect()


def test_ssh_detector_optimized_run_diagnosis():
    """Test SSH detector optimized run_diagnosis with batch execution"""
    from unittest.mock import MagicMock, patch
    from nastool_adapters.ssh_detector import RemoteSSHDetector

    detector = RemoteSSHDetector("192.168.1.100", username="admin", password="password")
    detector._connected = True

    mock_client = MagicMock()
    mock_transport = MagicMock()
    mock_transport.is_active.return_value = True
    mock_client.get_transport.return_value = mock_transport

    def exec_command_side_effect(command, timeout=None, get_pty=None):
        mock_stdout = MagicMock()
        mock_stderr = MagicMock()
        mock_channel = MagicMock()

        mock_channel.recv_exit_status.return_value = 0

        if "loadavg" in command:
            mock_stdout.read.return_value.decode.return_value = "0.50 0.60 0.70"
        elif "uptime -p" in command:
            mock_stdout.read.return_value.decode.return_value = "up 5 hours, 30 minutes"
        elif "ip addr" in command:
            mock_stdout.read.return_value.decode.return_value = "inet 192.168.1.100/24"
        elif "df -h" in command:
            mock_stdout.read.return_value.decode.return_value = "Filesystem Size Used Avail Use% Mounted on\n/dev/sda1 100G 50G 50G 50% /"
        elif "ps aux | wc -l" in command:
            mock_stdout.read.return_value.decode.return_value = "150"
        elif "top" in command:
            mock_stdout.read.return_value.decode.return_value = "50.0"
        elif "ping" in command:
            mock_stdout.read.return_value.decode.return_value = "64 bytes from 142.250.80.46: icmp_seq=1 ttl=117 time=14.5 ms"
        else:
            mock_stdout.read.return_value.decode.return_value = ""

        mock_stderr.read.return_value.decode.return_value = ""

        return (MagicMock(), mock_stdout, mock_stderr)

    mock_client.exec_command.side_effect = exec_command_side_effect

    with patch.object(detector, '_get_ssh_client', return_value=mock_client):
        results = detector.run_diagnosis(full_mode=False, use_batch=True)

        assert len(results) > 0
        assert any(r.check_id == "system_load" for r in results)
        assert any(r.check_id == "network_interfaces" for r in results)

    detector.disconnect()


if __name__ == "__main__":
    tests = [
        test_ssh_detector_batch_execution,
        test_ssh_detector_context_manager,
        test_ssh_detector_is_connected,
        test_ssh_detector_command_timeout,
        test_ssh_detector_optimized_get_device_info,
        test_ssh_detector_optimized_run_diagnosis,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            print(f"[PASS] {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {test.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed")
