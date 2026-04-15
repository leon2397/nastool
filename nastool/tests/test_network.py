"""
test_network.py — Unit tests for core/network.py
"""

import sys
import os
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.network import NetworkInterface, ConnectivityTest


class TestNetworkInterface(unittest.TestCase):
    """Test NetworkInterface dataclass"""

    def test_interface_defaults(self):
        iface = NetworkInterface()
        self.assertEqual(iface.name, "")

    def test_interface_with_values(self):
        iface = NetworkInterface(name="eth0", ip="192.168.1.100", up=True)
        self.assertEqual(iface.name, "eth0")
        self.assertEqual(iface.ip, "192.168.1.100")
        self.assertTrue(iface.up)


class TestConnectivityTest(unittest.TestCase):
    """Test ConnectivityTest dataclass"""

    def test_connectivity_failure(self):
        ct = ConnectivityTest(host="192.168.1.1", port=80, reachable=False)
        self.assertFalse(ct.reachable)

    def test_connectivity_success(self):
        ct = ConnectivityTest(host="120.77.249.3", port=8000, reachable=True, rtt_ms=15.5)
        self.assertTrue(ct.reachable)
        self.assertEqual(ct.rtt_ms, 15.5)
