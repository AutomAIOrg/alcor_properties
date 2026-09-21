# Login protection and Tailscale Funnel

All login attempts consume the IP and username budgets, including successful logins.
Existing accounts share a counter by user ID, using the same MySQL username comparison as login.
Unknown names retain a normalized-name counter.
Counters are shared in MySQL (InnoDB), with atomic admission and database time.
Defaults: 5 attempts per 900-second window, configurable through LOGIN_RATE_LIMIT_*.
Apply `alembic upgrade heads` before starting the API. A database error fails closed.

For HTTP Funnel use the Compose overlay `deploy/docker-compose.funnel.yml` ,
then `tailscale funnel --bg http://127.0.0.1:8080`.
Set FUNNEL_TRUSTED_PROXY_CIDRS in .env.production to the exact source IP (/32 or /128)
seen by Caddy from the local Tailscale daemon; Docker may translate it to its host gateway.
Do not use all private networks. The default only trusts loopback and is deliberately conservative.
The production Compose defaults WEB_BIND_IP to 127.0.0.1 (host loopback). Keep this setting for Funnel.
The overlay exposes Caddy only on host loopback, and assigns a dedicated fixed Caddy IP
trusted by the backend. Change the dedicated subnet if it overlaps an existing route.
Caddy walks XFF strictly and replaces the forwarded header with its verified client_ip;
FastAPI independently checks the immediate peer. Uvicorn header rewriting is disabled.
Without a trusted source, requests share the proxy's IP budget rather than trusting client headers.
TCP Funnel requires separately configured PROXY-protocol listeners; this overlay is HTTP only.

Before exposure, test from two external IPs and send forged X-Forwarded-For / X-Real-IP.
Verify IP budgets differ for real clients, forged prefixes do not change the selected IP,
and exceeding either budget returns 429 with Retry-After. This requires the actual host.

Counters contain hashed keys. Periodically delete expired rows, e.g. from a scheduled DB job:
`DELETE FROM auth_login_limits WHERE window_start < UNIX_TIMESTAMP() - 86400;`
Use retention longer than the configured window. Cleanup is operational, never part of admission.
