import pytest

from app.models.proxy_pool import ProxyPool, ProxyProtocol


def test_proxy_get_url_without_auth():
    proxy = ProxyPool()
    proxy.protocol = ProxyProtocol.HTTP
    proxy.host = "192.168.1.10"
    proxy.port = 3128
    proxy.username = None
    proxy.password = None

    assert proxy.get_url() == "http://192.168.1.10:3128"


def test_proxy_get_url_with_auth():
    proxy = ProxyPool()
    proxy.protocol = ProxyProtocol.SOCKS5
    proxy.host = "proxy.secure.io"
    proxy.port = 1080
    proxy.username = "user"
    proxy.password = "secret"

    assert proxy.get_url() == "socks5://user:secret@proxy.secure.io:1080"


def test_proxy_get_url_https_protocol():
    proxy = ProxyPool()
    proxy.protocol = ProxyProtocol.HTTPS
    proxy.host = "ssl-proxy.example.com"
    proxy.port = 443
    proxy.username = None
    proxy.password = None

    assert proxy.get_url() == "https://ssl-proxy.example.com:443"


def test_proxy_default_values():
    proxy = ProxyPool()
    proxy.protocol = ProxyProtocol.HTTP
    proxy.host = "localhost"
    proxy.port = 8080
    proxy.username = None
    proxy.password = None
    proxy.is_active = True
    proxy.success_rate = 1.0
    proxy.response_time_ms = 0

    assert proxy.is_active is True
    assert proxy.success_rate == 1.0
    assert proxy.response_time_ms == 0


def test_proxy_protocol_enum_values():
    assert ProxyProtocol.HTTP.value == "http"
    assert ProxyProtocol.HTTPS.value == "https"
    assert ProxyProtocol.SOCKS5.value == "socks5"
