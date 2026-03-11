"""URL validation to prevent SSRF (Server-Side Request Forgery).

Blocks webhook URLs that resolve to private/internal IP addresses.
"""

from __future__ import annotations

import ipaddress
import logging
import socket
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Private/reserved IP ranges that should be blocked
_BLOCKED_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # link-local
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),  # IPv6 private
    ipaddress.ip_network("fe80::/10"),  # IPv6 link-local
]


def validate_webhook_url(url: str) -> None:
    """Validate that a webhook URL is safe to call (no SSRF).

    Raises ValueError if the URL is invalid or resolves to a private IP.
    """
    parsed = urlparse(url)

    # Must be HTTPS (or HTTP in development)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Webhook URL must use http or https scheme")

    if not parsed.hostname:
        raise ValueError("Webhook URL must have a valid hostname")

    # Block common internal hostnames
    hostname = parsed.hostname.lower()
    blocked_hosts = {"localhost", "0.0.0.0", "metadata.google.internal", "169.254.169.254"}
    if hostname in blocked_hosts:
        raise ValueError(f"Webhook URL hostname '{hostname}' is not allowed")

    # Resolve hostname and check IP
    try:
        infos = socket.getaddrinfo(hostname, parsed.port or 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        raise ValueError(f"Cannot resolve webhook URL hostname '{hostname}'")

    for family, _, _, _, sockaddr in infos:
        ip = ipaddress.ip_address(sockaddr[0])
        for blocked in _BLOCKED_RANGES:
            if ip in blocked:
                raise ValueError(
                    f"Webhook URL resolves to private/reserved IP address ({ip}). "
                    "Only public IP addresses are allowed."
                )

    logger.debug("Webhook URL validated: %s", url)
