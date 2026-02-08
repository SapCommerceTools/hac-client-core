# Session management

The client automatically handles HAC sessions — login, CSRF token extraction, cookie management, and session caching.  This page explains how sessions work and how to manage them.

## How it works

1. On the first API call (or explicit `login()`), the client:
    - Fetches the HAC login page to get a CSRF token
    - Submits the Spring Security login form
    - Extracts the `JSESSIONID`, updated CSRF token, and optional `ROUTE` cookie
2. Session data is cached to disk (if `session_persistence=True`)
3. On subsequent runs, the client loads the cached session and validates it before use
4. If the session is expired or invalid, the client re-authenticates automatically

## Session caching

Sessions are cached to `~/.cache/hac-client/` by default.  Each session file is keyed by a hash of `(base_url, username, environment)`:

```python
client = HacClient(
    base_url="https://localhost:9002",
    auth_handler=auth,
    environment="local",          # tag sessions by environment
    session_persistence=True,     # enable caching (default)
)
```

!!! tip
    Use different `environment` values to maintain separate sessions for
    different targets (e.g. `"dev"`, `"staging"`, `"prod"`).

## Manage sessions directly

Use `SessionManager` to inspect and clean up cached sessions:

```python
from hac_client_core import SessionManager

mgr = SessionManager()

# List all cached sessions
for session in mgr.list_sessions():
    print(
        f"{session.environment:12s} "
        f"{session.base_url:40s} "
        f"created={session.created_at_formatted} "
        f"idle={session.idle_seconds:.0f}s"
    )

# Clear all sessions
cleared = mgr.clear_all_sessions()
print(f"Cleared {cleared} sessions")
```

### Custom cache directory

```python
from pathlib import Path

mgr = SessionManager(cache_dir=Path("/tmp/my-hac-cache"))
```

## Session validation

The client validates cached sessions by making a lightweight GET request to `/hac/` and checking if the response is the login page (redirect) or the authenticated dashboard:

- **Valid** — the session is reused, no re-login needed
- **Invalid** — the cached session is removed, and a fresh login is performed

## Disable caching

To always perform a fresh login:

```python
client = HacClient(
    base_url="https://localhost:9002",
    auth_handler=auth,
    session_persistence=False,
)
```

## What's cached

The session cache files contain:

| Field | Stored? | Description |
|---|---|---|
| `JSESSIONID` | ✅ | Java servlet session ID |
| `CSRF token` | ✅ | Spring Security CSRF token |
| `ROUTE` cookie | ✅ | Load balancer affinity (if present) |
| Password | ❌ | **Never stored** |

Files are plain JSON with filesystem-level permissions of the current user.  See [Security](../security.md) for details.
