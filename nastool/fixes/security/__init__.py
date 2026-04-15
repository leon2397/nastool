# fixes/security/__init__.py - Security fixes
from .disable_root_login import DisableRootLoginFix
from .enable_fail2ban import EnableFail2banFix
from .enforce_password_policy import EnforcePasswordPolicyFix
from .renew_ssl_cert import RenewSSLCertFix

__all__ = [
    "DisableRootLoginFix",
    "EnableFail2banFix",
    "EnforcePasswordPolicyFix",
    "RenewSSLCertFix",
]
