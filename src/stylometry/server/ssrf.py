"""Refuse server-side fetches of internal addresses (loopback, private ranges, cloud metadata)."""
import ipaddress
import socket
from urllib.parse import urlparse


class UrlNotAllowed(Exception):
    pass


def check(url: str) -> None:
    """Raise UrlNotAllowed unless url is http(s) and every address its host resolves to is public.

    ponytail: resolve-then-fetch leaves a DNS-rebinding window; close it with network egress rules.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise UrlNotAllowed("only http(s) URLs with a host are allowed")
    try:
        infos = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
    except socket.gaierror as e:
        raise UrlNotAllowed(f"cannot resolve host {parsed.hostname!r}") from e
    for info in infos:
        ip = ipaddress.ip_address(info[4][0].split("%")[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            raise UrlNotAllowed(f"host {parsed.hostname!r} resolves to a non-public address")
