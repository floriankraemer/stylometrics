import socket

import pytest

from stylometry.server import ssrf


def resolve_to(monkeypatch, ip):
    family = socket.AF_INET6 if ":" in ip else socket.AF_INET
    monkeypatch.setattr(ssrf.socket, "getaddrinfo", lambda *a, **k: [(family, 0, 0, "", (ip, 0))])


@pytest.mark.parametrize("ip", ["127.0.0.1", "10.1.2.3", "192.168.0.1", "172.16.0.9", "169.254.169.254",
                                "0.0.0.0", "::1", "fe80::1", "224.0.0.1"])
def test_blocks_non_public(monkeypatch, ip):
    resolve_to(monkeypatch, ip)
    with pytest.raises(ssrf.UrlNotAllowed):
        ssrf.check("http://example.test/")


def test_allows_public(monkeypatch):
    resolve_to(monkeypatch, "93.184.216.34")
    ssrf.check("https://example.test/page")


def test_blocks_any_private_among_many(monkeypatch):
    monkeypatch.setattr(ssrf.socket, "getaddrinfo", lambda *a, **k: [
        (socket.AF_INET, 0, 0, "", ("93.184.216.34", 0)), (socket.AF_INET, 0, 0, "", ("10.0.0.1", 0))])
    with pytest.raises(ssrf.UrlNotAllowed):
        ssrf.check("http://example.test/")


@pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://example.test/", "http:///nohost"])
def test_blocks_bad_scheme_or_host(url):
    with pytest.raises(ssrf.UrlNotAllowed):
        ssrf.check(url)


def test_unresolvable(monkeypatch):
    def boom(*a, **k):
        raise socket.gaierror
    monkeypatch.setattr(ssrf.socket, "getaddrinfo", boom)
    with pytest.raises(ssrf.UrlNotAllowed):
        ssrf.check("http://nope.invalid/")
