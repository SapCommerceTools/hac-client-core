# Security considerations

This page documents how the library handles credentials, sessions, and network security.

## Credentials

### In memory

`BasicAuthHandler` stores the password as a private attribute (`_password`).  The reference is set to `None` in `__del__()` when the object is garbage-collected.

!!! warning
    Python does not guarantee when `__del__` runs, and the string object
    may still live in memory until the garbage collector reclaims it.
    This is a best-effort cleanup, not a security guarantee.

For stronger credential handling:

- Use a custom `AuthHandler` that fetches credentials on-demand from a secrets manager (e.g. AWS Secrets Manager, HashiCorp Vault)
- Keep the `BasicAuthHandler` instance short-lived

### On disk

**Passwords are never written to disk.**  The session cache stores only:

- `JSESSIONID`
- CSRF token
- `ROUTE` cookie (if present)
- Metadata (URL, username, timestamps)

## Session cache

### Location

Sessions are cached to `~/.cache/hac-client/` by default.  Each session is a JSON file named `session_<hash>.json`, where the hash is derived from `(base_url, username, environment)`.

### Permissions

Files are created with the default permissions of the current user.  On multi-user systems, ensure the cache directory has appropriate permissions:

```bash
chmod 700 ~/.cache/hac-client/
```

### Sensitivity

The session cache contains **session IDs and CSRF tokens**, which grant authenticated access to the HAC for the lifetime of the session.  Treat these files as sensitive.

To clear all cached sessions:

```python
from hac_client_core import SessionManager

SessionManager().clear_all_sessions()
```

Or delete the cache directory:

```bash
rm -rf ~/.cache/hac-client/
```

## CSRF protection

The client automatically:

1. Extracts the CSRF token from the HAC login page (`<input name="_csrf">` or `<meta name="_csrf">`)
2. Includes it as `_csrf` in the login form submission
3. Sends it as the `X-CSRF-TOKEN` header on all subsequent API requests

This matches the behaviour of the HAC web UI and satisfies Spring Security's CSRF validation.

## SSL / TLS

By default, the client verifies SSL certificates.  The `ignore_ssl=True` option disables verification:

```python
client = HacClient(
    base_url="https://localhost:9002",
    auth_handler=auth,
    ignore_ssl=True,  # disables certificate checks
)
```

!!! danger
    `ignore_ssl=True` makes the connection vulnerable to man-in-the-middle
    attacks.  Use it **only** for local development with self-signed
    certificates.

For production, ensure the HAC endpoint has a valid certificate (or add the CA to the system trust store).

## Network considerations

- All communication is over HTTPS (the library does not enforce this, but HAC should always be behind TLS)
- The `ROUTE` cookie is forwarded for load balancer affinity in clustered environments
- HTTP timeouts are configurable via the `timeout` parameter (default: 30 seconds)
