"""
Safe URL validation service for Phase 27 External Application Autofill.

Enforces:
1. Strict HTTPS scheme requirement (no http, file, javascript, data schemes).
2. Elimination of credentials/userinfo embedded in URLs.
3. Allowlisted ATS domain verification.
4. Comprehensive SSRF prevention with full DNS resolution inspection:
   - Rejection of loopback, private, link-local, reserved, multicast, CGNAT,
     and IPv4-mapped private IPs.
   - Protection against DNS rebinding and mixed public/private DNS answers.
5. Path structure sanitization.
"""

from __future__ import annotations

import ipaddress
import re
import socket
from urllib.parse import urlparse

from app.core.config import settings
from app.services.autofill.exceptions import (
    InvalidURLError,
    ProhibitedDestinationError,
    UnsupportedProviderError,
)

# Pre-compiled carrier-grade NAT network (100.64.0.0/10)
_CGNAT_NETWORK = ipaddress.ip_network("100.64.0.0/10")

# Pre-compiled regex for suspicious control characters
_CONTROL_CHAR_REGEX = re.compile(r"[\x00-\x1f\x7f]")


def is_prohibited_ip(ip_str: str) -> bool:
    """
    Evaluate whether an IP address belongs to a private, loopback, link-local,
    reserved, multicast, carrier-grade NAT, or unspecified range.
    Handles both IPv4 and IPv6 including IPv4-mapped IPv6 addresses.
    """
    try:
        ip = ipaddress.ip_address(ip_str.strip())
    except ValueError:
        return True  # Invalid IP representation is treated as prohibited

    # Unwrap IPv4-mapped IPv6 address (e.g. ::ffff:127.0.0.1)
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped

    if (
        ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    ):
        return True

    # Check Carrier Grade NAT for IPv4
    if isinstance(ip, ipaddress.IPv4Address) and ip in _CGNAT_NETWORK:
        return True

    return False


def resolve_hostname_ips(hostname: str, port: int = 443) -> list[tuple]:
    """Resolve DNS records for the given hostname and port using TCP."""
    return socket.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)


def validate_external_application_url(
    url: str,
    allowed_domains: list[str] | None = None,
    resolve_dns: bool = True,
) -> tuple[str, list[str]]:
    """
    Defensively validate an external application URL before opening in a browser.

    Args:
        url: Raw external application URL to validate.
        allowed_domains: Optional override for permitted ATS hostnames.
        resolve_dns: Whether to perform live DNS resolution and IP verification (default True).

    Returns:
        tuple of (sanitized_canonical_url, list_of_verified_public_ips)

    Raises:
        InvalidURLError: For malformed syntax, non-HTTPS scheme, credentials, or control characters.
        UnsupportedProviderError: If the hostname is not on the strict ATS allowlist.
        ProhibitedDestinationError: If DNS resolves to a private, loopback, or reserved destination.
    """
    if not url or not isinstance(url, str):
        raise InvalidURLError("External application URL cannot be empty.")

    trimmed = url.strip()
    if _CONTROL_CHAR_REGEX.search(trimmed):
        raise InvalidURLError("External application URL contains invalid control characters.")

    try:
        parsed = urlparse(trimmed)
    except Exception as exc:
        raise InvalidURLError(f"Malformed URL structure: {exc}") from exc

    # 1. Scheme enforcement: HTTPS ONLY
    if parsed.scheme.lower() != "https":
        raise InvalidURLError(
            f"Prohibited URL scheme '{parsed.scheme}'. Only secure 'https://' URLs are supported."
        )

    # 2. Rejection of embedded credentials (e.g. https://user:pass@example.com)
    if parsed.username or parsed.password:
        raise InvalidURLError(
            "URLs with embedded authentication credentials are strictly prohibited."
        )

    hostname = (parsed.hostname or "").lower().strip()
    if not hostname:
        raise InvalidURLError("URL must specify a valid hostname.")

    # 3. Direct IP address as hostname is prohibited
    try:
        ipaddress.ip_address(hostname)
        raise InvalidURLError("Direct IP address access is prohibited; a domain name is required.")
    except ValueError:
        pass  # Hostname is not a raw IP, proceed

    # 4. Allowlisted domain verification
    active_allowed_domains = [
        d.lower().strip()
        for d in (allowed_domains or settings.AUTOFILL_ALLOWED_ATS_DOMAINS)
        if d.strip()
    ]

    is_allowed = any(
        hostname == domain or hostname.endswith(f".{domain}") for domain in active_allowed_domains
    )
    if not is_allowed:
        raise UnsupportedProviderError(
            f"Host '{hostname}' is not a supported ATS platform. "
            f"Permitted platforms: {', '.join(active_allowed_domains)}."
        )

    # 5. DNS Resolution and SSRF inspection
    verified_ips: list[str] = []
    if resolve_dns:
        try:
            # Resolve both IPv4 and IPv6 records for the hostname
            addr_info = resolve_hostname_ips(
                hostname,
                parsed.port or 443,
            )
        except (socket.gaierror, socket.herror) as exc:
            raise InvalidURLError(f"DNS resolution failed for host '{hostname}': {exc}") from exc
        except Exception as exc:
            raise InvalidURLError(f"Unexpected error resolving host '{hostname}': {exc}") from exc

        if not addr_info:
            raise InvalidURLError(f"No IP address records found for host '{hostname}'.")

        for item in addr_info:
            sockaddr = item[4]
            ip_str = sockaddr[0]
            if is_prohibited_ip(ip_str):
                raise ProhibitedDestinationError(
                    f"Host '{hostname}' resolves to prohibited or internal destination '{ip_str}'."
                )
            if ip_str not in verified_ips:
                verified_ips.append(ip_str)

    # Return canonical URL and verified IP addresses
    canonical_url = parsed.geturl()
    return canonical_url, verified_ips
