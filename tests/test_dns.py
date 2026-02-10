"""Tests for the DNS resolution helper."""

import socket
from unittest.mock import patch

import pytest

from bpl.dns import resolve_all

# Realistic getaddrinfo return format:
# (family, type, proto, canonname, sockaddr)
# sockaddr is (ip, port) for IPv4, (ip, port, flow, scope) for IPv6.

_IPV4_RESULT = (
    socket.AF_INET,
    socket.SOCK_STREAM,
    6,
    "",
    ("93.184.216.34", 443),
)

_IPV4_RESULT_2 = (
    socket.AF_INET,
    socket.SOCK_STREAM,
    6,
    "",
    ("93.184.216.35", 443),
)

_IPV6_RESULT = (
    socket.AF_INET6,
    socket.SOCK_STREAM,
    6,
    "",
    ("2606:2800:220:1:248:1893:25c8:1946", 443, 0, 0),
)


class TestResolveAll:
    """resolve_all() wraps socket.getaddrinfo correctly."""

    @patch("bpl.dns.socket.getaddrinfo")
    def test_single_ipv4(self, mock_gai: patch) -> None:
        mock_gai.return_value = [_IPV4_RESULT]

        result = resolve_all("example.com", port=443)

        assert result == [("93.184.216.34", 443)]
        mock_gai.assert_called_once_with(
            "example.com",
            443,
            family=socket.AF_UNSPEC,
            type=socket.SOCK_STREAM,
        )

    @patch("bpl.dns.socket.getaddrinfo")
    def test_multiple_ipv4(self, mock_gai: patch) -> None:
        mock_gai.return_value = [_IPV4_RESULT, _IPV4_RESULT_2]

        result = resolve_all("example.com", port=443)

        assert result == [("93.184.216.34", 443), ("93.184.216.35", 443)]

    @patch("bpl.dns.socket.getaddrinfo")
    def test_mixed_ipv4_ipv6(self, mock_gai: patch) -> None:
        mock_gai.return_value = [_IPV4_RESULT, _IPV6_RESULT]

        result = resolve_all("example.com", port=443)

        assert len(result) == 2
        assert ("93.184.216.34", 443) in result
        assert ("2606:2800:220:1:248:1893:25c8:1946", 443) in result

    @patch("bpl.dns.socket.getaddrinfo")
    def test_deduplication(self, mock_gai: patch) -> None:
        """Duplicate entries from getaddrinfo are collapsed."""
        mock_gai.return_value = [_IPV4_RESULT, _IPV4_RESULT, _IPV4_RESULT]

        result = resolve_all("example.com", port=443)

        assert result == [("93.184.216.34", 443)]

    @patch("bpl.dns.socket.getaddrinfo")
    def test_preserves_order(self, mock_gai: patch) -> None:
        """First occurrence wins when deduplicating."""
        mock_gai.return_value = [
            _IPV4_RESULT_2,
            _IPV4_RESULT,
            _IPV4_RESULT_2,
        ]

        result = resolve_all("example.com", port=443)

        assert result == [("93.184.216.35", 443), ("93.184.216.34", 443)]

    @patch("bpl.dns.socket.getaddrinfo")
    def test_default_port_zero(self, mock_gai: patch) -> None:
        """Port defaults to 0 when not specified."""
        mock_gai.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("1.2.3.4", 0)),
        ]

        result = resolve_all("example.com")

        mock_gai.assert_called_once_with(
            "example.com",
            0,
            family=socket.AF_UNSPEC,
            type=socket.SOCK_STREAM,
        )
        assert result == [("1.2.3.4", 0)]

    @patch("bpl.dns.socket.getaddrinfo")
    def test_gaierror_propagates(self, mock_gai: patch) -> None:
        """socket.gaierror is not caught — it propagates to callers."""
        mock_gai.side_effect = socket.gaierror(
            socket.EAI_NONAME, "Name or service not known"
        )

        with pytest.raises(socket.gaierror, match="Name or service not known"):
            resolve_all("nonexistent.invalid")

    @patch("bpl.dns.socket.getaddrinfo")
    def test_empty_result(self, mock_gai: patch) -> None:
        """An empty getaddrinfo result returns an empty list."""
        mock_gai.return_value = []

        result = resolve_all("example.com", port=443)

        assert result == []
