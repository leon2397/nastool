# Network checks module
# After @check() decoration: function name IS the class.
from . import (
    internet_access, dns_cache, dns_resolve, dns_coverage,
    mtu_check, proxy_check, wifi_check, bandwidth_check,
    latency_check, route_check, port_conflict,
    # nas_backend and nic_speed preserved as class (complex)
)

InternetAccessCheck = internet_access
DNSCacheCheck      = dns_cache
DNSResolveCheck    = dns_resolve
DNSCoverageCheck   = dns_coverage
MTUCheck           = mtu_check
ProxyCheck         = proxy_check
WiFiCheck          = wifi_check
BandwidthCheck     = bandwidth_check
LatencyCheck       = latency_check
RouteCheck         = route_check
PortConflictCheck  = port_conflict

# Complex checks preserved as classes
from .nas_backend import NASBackendCheck
from .nic_speed import NICSpeedCheck
from .network_latency import NetworkLatencyCheck

__all__ = [
    "InternetAccessCheck", "DNSCacheCheck", "DNSResolveCheck",
    "DNSCoverageCheck", "MTUCheck", "ProxyCheck", "WiFiCheck",
    "BandwidthCheck", "LatencyCheck", "RouteCheck", "PortConflictCheck",
    "NASBackendCheck", "NICSpeedCheck", "NetworkLatencyCheck",
]
