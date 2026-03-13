"""Tests for api/services/url_validator.py — SSRF protection."""

from __future__ import annotations

import socket
from unittest.mock import patch

import pytest

from api.services.url_validator import validate_webhook_url


class TestSchemeValidation:
    def test_https_allowed(self):
        # Will raise ValueError on DNS resolution or private IP, not on scheme
        with pytest.raises(ValueError, match="Cannot resolve"):
            validate_webhook_url("https://nonexistent-host-abc123.example.com/hook")

    def test_http_allowed(self):
        with pytest.raises(ValueError, match="Cannot resolve"):
            validate_webhook_url("http://nonexistent-host-abc123.example.com/hook")

    def test_ftp_blocked(self):
        with pytest.raises(ValueError, match="http or https"):
            validate_webhook_url("ftp://example.com/hook")

    def test_file_blocked(self):
        with pytest.raises(ValueError, match="http or https"):
            validate_webhook_url("file:///etc/passwd")

    def test_javascript_blocked(self):
        with pytest.raises(ValueError, match="http or https"):
            validate_webhook_url("javascript:alert(1)")

    def test_empty_scheme(self):
        with pytest.raises(ValueError):
            validate_webhook_url("://example.com/hook")


class TestHostnameBlocking:
    def test_localhost_blocked(self):
        with pytest.raises(ValueError, match="not allowed"):
            validate_webhook_url("http://localhost/hook")

    def test_localhost_uppercase_blocked(self):
        with pytest.raises(ValueError, match="not allowed"):
            validate_webhook_url("http://LOCALHOST/hook")

    def test_zero_ip_blocked(self):
        with pytest.raises(ValueError, match="not allowed"):
            validate_webhook_url("http://0.0.0.0/hook")

    def test_metadata_google_blocked(self):
        with pytest.raises(ValueError, match="not allowed"):
            validate_webhook_url("http://metadata.google.internal/computeMetadata/v1/")

    def test_aws_metadata_blocked(self):
        with pytest.raises(ValueError, match="not allowed"):
            validate_webhook_url("http://169.254.169.254/latest/meta-data/")

    def test_no_hostname(self):
        with pytest.raises(ValueError, match="valid hostname"):
            validate_webhook_url("http:///hook")


class TestPrivateIPBlocking:
    """Test that resolved private IPs are blocked."""

    def _mock_getaddrinfo(self, ip: str):
        """Return a mock getaddrinfo result for a given IP."""
        return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (ip, 443))]

    def test_10_x_blocked(self):
        with patch("api.services.url_validator.socket.getaddrinfo", return_value=self._mock_getaddrinfo("10.0.0.1")):
            with pytest.raises(ValueError, match="private/reserved"):
                validate_webhook_url("https://internal.example.com/hook")

    def test_172_16_blocked(self):
        with patch("api.services.url_validator.socket.getaddrinfo", return_value=self._mock_getaddrinfo("172.16.0.1")):
            with pytest.raises(ValueError, match="private/reserved"):
                validate_webhook_url("https://internal.example.com/hook")

    def test_192_168_blocked(self):
        with patch("api.services.url_validator.socket.getaddrinfo", return_value=self._mock_getaddrinfo("192.168.1.1")):
            with pytest.raises(ValueError, match="private/reserved"):
                validate_webhook_url("https://internal.example.com/hook")

    def test_127_0_blocked(self):
        with patch("api.services.url_validator.socket.getaddrinfo", return_value=self._mock_getaddrinfo("127.0.0.1")):
            with pytest.raises(ValueError, match="private/reserved"):
                validate_webhook_url("https://internal.example.com/hook")

    def test_link_local_blocked(self):
        with patch("api.services.url_validator.socket.getaddrinfo", return_value=self._mock_getaddrinfo("169.254.1.1")):
            with pytest.raises(ValueError, match="private/reserved"):
                validate_webhook_url("https://internal.example.com/hook")

    def test_public_ip_allowed(self):
        with patch("api.services.url_validator.socket.getaddrinfo", return_value=self._mock_getaddrinfo("93.184.216.34")):
            # Should NOT raise
            validate_webhook_url("https://example.com/hook")

    def test_ipv6_loopback_blocked(self):
        mock_result = [(socket.AF_INET6, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("::1", 443, 0, 0))]
        with patch("api.services.url_validator.socket.getaddrinfo", return_value=mock_result):
            with pytest.raises(ValueError, match="private/reserved"):
                validate_webhook_url("https://internal.example.com/hook")


class TestDNSResolution:
    def test_unresolvable_host(self):
        with pytest.raises(ValueError, match="Cannot resolve"):
            validate_webhook_url("https://this-domain-definitely-does-not-exist-xyz123.example.com/hook")
