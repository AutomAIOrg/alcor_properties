"""Trust only explicitly configured peers; walk XFF from the nearest hop."""

import ipaddress
from collections.abc import Sequence

from starlette.requests import Request


def parse_trusted_proxy_cidrs(raw: str | Sequence[str]):
    parts = raw.split(",") if isinstance(raw, str) else raw
    # Fail configuration on typos rather than silently broadening trust.
    return [ipaddress.ip_network(part.strip(), strict=False) for part in parts if part.strip()]


def resolve_client_ip(request: Request, trusted_proxy_cidrs) -> str:
    if request.client is None:
        return "unknown"
    try:
        peer = ipaddress.ip_address(request.client.host)
    except ValueError:
        return "unknown"

    def trusted(ip):
        return any(ip in network for network in trusted_proxy_cidrs)

    if not trusted(peer):
        return str(peer)
    raw = request.headers.get("x-forwarded-for", "")
    if not raw or len(raw) > 2048:
        return str(peer)
    try:
        hops = [ipaddress.ip_address(part.strip()) for part in raw.split(",")]
    except ValueError:
        return str(peer)
    for hop in reversed(hops):
        if not trusted(hop):
            return str(hop)
    return str(peer)
