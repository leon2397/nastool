# Security checks module
# After @check() decoration: function name IS the class.
from . import (
    openssl_version, firewall, ssh_root, ssh_config,
    fail2ban, clamav_check, port_scan, selinux,
)

OpenSSLVersionCheck = openssl_version
FirewallCheck      = firewall
SSHRootCheck       = ssh_root
SSHConfigCheck     = ssh_config
Fail2banCheck      = fail2ban
ClamAVCheck        = clamav_check
PortScanCheck      = port_scan
SELinuxCheck       = selinux

# Complex checks preserved as classes
from .ssl_cert import SSLCertCheck
from .ssl_cert_check import SSLCertCheck as SSLCertCheckDays
from .login_failures import LoginFailuresCheck

__all__ = [
    "OpenSSLVersionCheck", "FirewallCheck", "SSHRootCheck",
    "SSHConfigCheck", "Fail2banCheck", "ClamAVCheck",
    "PortScanCheck", "SELinuxCheck",
    "SSLCertCheck", "SSLCertCheckDays", "LoginFailuresCheck",
]
