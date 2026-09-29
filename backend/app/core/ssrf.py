"""Server-Side Request Forgery (SSRF) protection and URL validation gates."""

import ipaddress
import socket
from urllib.parse import urlparse
from app.core.exceptions import AppException
from app.core.logging import get_logger

logger = get_logger(__name__)

# Disallowed private, loopback, link-local, and cloud metadata CIDR ranges
DISALLOWED_NETWORKS = [
    # IPv4 Loopback
    ipaddress.ip_network("127.0.0.0/8"),
    # IPv4 Private
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    # IPv4 Link-Local / AWS/GCP/Azure Metadata (169.254.169.254)
    ipaddress.ip_network("169.254.0.0/16"),
    # IPv4 Carrier-Grade NAT
    ipaddress.ip_network("100.64.0.0/10"),
    # IPv4 Broadcast / Current Network
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("255.255.255.255/32"),
    # IPv4 Multicast
    ipaddress.ip_network("224.0.0.0/4"),
    # IPv4 Documentation / Benchmark
    ipaddress.ip_network("192.0.2.0/24"),
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
    ipaddress.ip_network("198.18.0.0/15"),
    # IPv6 Loopback
    ipaddress.ip_network("::1/128"),
    # IPv6 Unspecified
    ipaddress.ip_network("::/128"),
    # IPv6 Unique Local Address (ULA)
    ipaddress.ip_network("fc00::/7"),
    # IPv6 Link-Local
    ipaddress.ip_network("fe80::/10"),
    # IPv6 Multicast
    ipaddress.ip_network("ff00::/8"),
]

BLOCKED_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
    "metadata",
    "instance-data",
}

BLOCKED_SUFFIXES = (
    ".localhost",
    ".local",
    ".internal",
    ".corp",
    ".lan",
    ".home",
)


class SSRFSecurityException(AppException):
    """Raised when an outbound URL violates SSRF network boundaries."""
    def __init__(self, message: str):
        super().__init__(status_code=400, code="SSRF_DESTINATION_FORBIDDEN", message=message)


def validate_destination_url(url: str) -> str:
    """Validate that target URL is a safe public HTTP or HTTPS destination.

    Performs scheme validation, hostname check, and synchronous DNS resolution
    to ensure destination does not point to internal/private networks or cloud metadata.
    """
    if not url or not isinstance(url, str):
        raise SSRFSecurityException("Webhook URL is empty or invalid.")

    try:
        parsed = urlparse(url.strip())
    except Exception as e:
        raise SSRFSecurityException(f"Invalid URL format: {e}")

    # 1. Scheme check: only http and https allowed
    if parsed.scheme.lower() not in ("http", "https"):
        raise SSRFSecurityException(f"Scheme '{parsed.scheme}' is not permitted. Only HTTP and HTTPS are allowed.")

    hostname = parsed.hostname
    if not hostname:
        raise SSRFSecurityException("URL is missing a valid hostname or host IP.")

    lower_host = hostname.lower()

    # 2. Hostname blocklist
    if lower_host in BLOCKED_HOSTNAMES or any(lower_host.endswith(suffix) for suffix in BLOCKED_SUFFIXES):
        logger.warning("SSRF blocked attempt to reach forbidden hostname: %s", hostname)
        raise SSRFSecurityException(f"Destination hostname '{hostname}' is not permitted.")

    # 3. DNS resolution and IP address boundary check
    port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
    try:
        addr_infos = socket.getaddrinfo(hostname, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise SSRFSecurityException(f"Failed to resolve destination hostname '{hostname}': {e}")

    if not addr_infos:
        raise SSRFSecurityException(f"No IP addresses resolved for hostname '{hostname}'.")

    for family, _, _, _, sockaddr in addr_infos:
        ip_str = sockaddr[0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            raise SSRFSecurityException(f"Invalid resolved IP address '{ip_str}'.")

        # Check against all disallowed networks
        for net in DISALLOWED_NETWORKS:
            if ip_obj in net:
                logger.warning("SSRF blocked attempt to reach restricted IP: %s (hostname: %s)", ip_str, hostname)
                raise SSRFSecurityException(
                    f"Destination resolves to restricted or private IP address ({ip_str}). Outbound access forbidden."
                )

    return url.strip()
