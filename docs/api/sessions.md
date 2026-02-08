# Session management API

::: hac_client_core.session

Classes for managing HAC session persistence and caching.

---

## SessionManager

```python
from hac_client_core import SessionManager

mgr = SessionManager()  # uses ~/.cache/hac-client/
```

Manages persisted HAC sessions.  Marked `@final` — not intended for subclassing.

### Constructor

| Parameter | Type | Default | Description |
|---|---|---|---|
| `cache_dir` | `Path \| None` | `None` | Cache directory (default: `~/.cache/hac-client/`) |

### Methods

#### `load_session()`

```python
mgr.load_session(
    base_url: str,
    username: str,
    environment: str,
) -> SessionMetadata | None
```

Load a cached session.  Returns `None` if no session exists or the cache file is corrupted (in which case the file is deleted).

---

#### `save_session()`

```python
mgr.save_session(
    base_url: str,
    username: str,
    environment: str,
    session_id: str,
    csrf_token: str,
    route_cookie: str | None = None,
) -> None
```

Save a session to disk.  If a session already exists for the same key, the `created_at` timestamp is preserved; only `last_used_at` is updated.

---

#### `touch_session()`

```python
mgr.touch_session(
    base_url: str,
    username: str,
    environment: str,
) -> None
```

Update the `last_used_at` timestamp of an existing cached session.

---

#### `remove_session()`

```python
mgr.remove_session(
    base_url: str,
    username: str,
    environment: str,
) -> None
```

Delete a specific cached session file.

---

#### `list_sessions()`

```python
mgr.list_sessions() -> list[SessionMetadata]
```

List all cached sessions, sorted by `last_used_at` (most recent first).

---

#### `clear_all_sessions()`

```python
mgr.clear_all_sessions() -> int
```

Delete all cached session files.  Returns the number of sessions cleared.

---

## SessionMetadata

Dataclass representing a persisted session.

### Fields

| Field | Type | Description |
|---|---|---|
| `session_id` | `str` | `JSESSIONID` |
| `csrf_token` | `str` | CSRF token |
| `route_cookie` | `str \| None` | `ROUTE` cookie for load balancer affinity |
| `environment` | `str` | Environment identifier |
| `base_url` | `str` | HAC base URL |
| `username` | `str` | Username |
| `created_at` | `float` | Unix timestamp when the session was created |
| `last_used_at` | `float` | Unix timestamp when the session was last used |
| `is_authenticated` | `bool` | Whether the session is authenticated (default `True`) |

### Properties

| Property | Type | Description |
|---|---|---|
| `age_seconds` | `float` | Seconds since session creation |
| `idle_seconds` | `float` | Seconds since last use |
| `created_at_formatted` | `str` | `YYYY-MM-DD HH:MM:SS` |
| `last_used_at_formatted` | `str` | `YYYY-MM-DD HH:MM:SS` |
