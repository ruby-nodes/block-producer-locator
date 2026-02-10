"""DNS resolution helper for probe discovery."""

import logging
import socket

logger = logging.getLogger(__name__)


def resolve_all(hostname: str, port: int = 0) -> list[tuple[str, int]]:
    """Resolve a hostname to all A and AAAA records.

    Wraps ``socket.getaddrinfo`` to return deduplicated ``(ip, port)``
    pairs for both IPv4 and IPv6 addresses.

    Args:
        hostname: The hostname to resolve (e.g.
            ``"mainnet-sequencer.base.org"``).
        port: Service port to pass to ``getaddrinfo``.  Defaults to ``0``
            (any port).

    Returns:
        A deduplicated list of ``(ip, port)`` tuples.

    Raises:
        socket.gaierror: If DNS resolution fails entirely.
    """
    logger.debug("Resolving %s (port=%d)", hostname, port)

    results = socket.getaddrinfo(
        hostname,
        port,
        family=socket.AF_UNSPEC,
        type=socket.SOCK_STREAM,
    )

    seen: set[tuple[str, int]] = set()
    out: list[tuple[str, int]] = []
    for family, _type, _proto, _canonname, sockaddr in results:
        # sockaddr is (ip, port) for AF_INET, (ip, port, flow, scope) for AF_INET6
        ip = sockaddr[0]
        resolved_port = sockaddr[1]
        key = (ip, resolved_port)
        if key not in seen:
            seen.add(key)
            out.append(key)

    logger.debug("Resolved %s → %d unique address(es)", hostname, len(out))
    return out
