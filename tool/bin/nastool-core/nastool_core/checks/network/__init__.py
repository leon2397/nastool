# Network checks module
# After @check() decoration: function name IS the class.
from . import internet_access
from . import dns_cache
from . import dns_resolve
from . import dns_coverage
from . import mtu_check
from . import proxy_check
from . import wifi_check
from . import bandwidth_check
from . import latency_check
from . import route_check
from . import port_conflict
from . import nas_backend
from . import nic_speed
from . import network_latency

# Assign module references to class names for backward compatibility
InternetAccessCheck = internet_access
DNSCacheCheck = dns_cache
DNSResolveCheck = dns_resolve
DNSCoverageCheck = dns_coverage
MTUCheck = mtu_check
ProxyCheck = proxy_check
WiFiCheck = wifi_check
BandwidthCheck = bandwidth_check
LatencyCheck = latency_check
RouteCheck = route_check
PortConflictCheck = port_conflict
NASBackendCheck = nas_backend
NICSpeedCheck = nic_speed
NetworkLatencyCheck = network_latency

# Enhanced diagnostic modules (classes)
from .network_status_checker import NetworkStatusChecker
from .network_quality_checker import NetworkQualityChecker
from .dns_diagnostic import DNSDiagnostic

__all__ = [
    'InternetAccessCheck',
    'DNSCacheCheck',
    'DNSResolveCheck',
    'DNSCoverageCheck',
    'MTUCheck',
    'ProxyCheck',
    'WiFiCheck',
    'BandwidthCheck',
    'LatencyCheck',
    'RouteCheck',
    'PortConflictCheck',
    'NASBackendCheck',
    'NICSpeedCheck',
    'NetworkLatencyCheck',
    'NetworkStatusChecker',
    'NetworkQualityChecker',
    'DNSDiagnostic',
]
