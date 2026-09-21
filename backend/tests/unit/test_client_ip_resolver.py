from types import SimpleNamespace

import pytest

from infrastructure.security.client_ip_resolver import parse_trusted_proxy_cidrs, resolve_client_ip


def request(peer, xff="", real=""):
    return SimpleNamespace(
        client=SimpleNamespace(host=peer), headers={"x-forwarded-for": xff, "x-real-ip": real}
    )


def test_untrusted_peer_ignores_headers():
    assert resolve_client_ip(request("203.0.113.1", "1.1.1.1"), []) == "203.0.113.1"


def test_trusted_chain_discards_spoofed_left_prefix():
    trust = parse_trusted_proxy_cidrs("172.18.0.5/32,127.0.0.1/32")
    assert (
        resolve_client_ip(request("172.18.0.5", "1.1.1.1, 203.0.113.1, 127.0.0.1"), trust)
        == "203.0.113.1"
    )


@pytest.mark.parametrize("xff", ["bad, 203.0.113.1", "", "1.1.1.1,", "x" * 2049])
def test_bad_chain_and_real_ip_fail_closed(xff):
    assert (
        resolve_client_ip(
            request("172.18.0.5", xff, "1.1.1.1"), parse_trusted_proxy_cidrs("172.18.0.5/32")
        )
        == "172.18.0.5"
    )


def test_invalid_config_is_rejected():
    with pytest.raises(ValueError):
        parse_trusted_proxy_cidrs("not-a-network")


def test_ipv6():
    assert (
        resolve_client_ip(request("::1", "2001:db8::1"), parse_trusted_proxy_cidrs("::1/128"))
        == "2001:db8::1"
    )


def test_missing_peer_does_not_trust_forwarded_headers():
    req = SimpleNamespace(client=None, headers={"x-forwarded-for": "203.0.113.1"})
    assert resolve_client_ip(req, parse_trusted_proxy_cidrs("127.0.0.1/32")) == "unknown"
