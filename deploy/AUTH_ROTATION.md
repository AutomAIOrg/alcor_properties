# Session-bound refresh rotation

Apply `alembic upgrade heads` before starting the updated API. The follow-up migration
supports databases that already applied c8e1a4b7d2f0; it replaces the per-user jti with
auth_sessions and increments every user's token version to reject all legacy tokens.
Users must sign in again once after migration. Each subsequent login creates an independent family.

Refresh atomically replaces that family's jti. Reuse revokes the family, including its access
tokens; other devices remain signed in. A user token-version bump revokes all families.
Concurrent reuse fails closed: one rotation may succeed before the competing request revokes
its family. Angular serializes concurrent refreshes within a tab and uses Web Locks across
tabs when supported. Clients without Web Locks must avoid concurrent refreshes themselves.
JWT_ACCESS_TOKEN_EXPIRE_MINUTES and JWT_REFRESH_TOKEN_EXPIRE_DAYS apply to every new pair.
Refresh expiry slides at each successful rotation. Expired families can be removed after expiry.

Run MySQL concurrency tests against a disposable server via AUTH_TEST_MYSQL_URL. Tests create
and drop randomly named databases, never the application's existing database.
