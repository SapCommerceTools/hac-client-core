# hac-client-core

Python client library for the **SAP Commerce HAC** (Hybris Administration Console) HTTP API.

Execute Groovy scripts, run FlexibleSearch queries, import Impex data, and trigger system updates — all from Python, with automatic session management and CSRF handling.

## Features

- **Groovy script execution** — run arbitrary Groovy in commit or rollback mode
- **FlexibleSearch queries** — execute queries with typed result objects
- **Impex import** — import Impex content with configurable validation
- **System update** — trigger updates, select patches/parameters, poll logs
- **Session management** — automatic login, CSRF tokens, session caching across runs
- **Pluggable authentication** — ships with Basic Auth; extend `AuthHandler` for OAuth, JWT, API keys, etc.
- **Fully typed** — complete type annotations with a `py.typed` marker (PEP 561)

## Requirements

- Python ≥ 3.12
- A running SAP Commerce instance with HAC enabled

## Installation

Install from PyPI (once published):

```bash
pip install hac-client-core
```

Or install directly from the repository:

```bash
pip install git+https://github.com/SapCommerceTools/ha-client-core.git
```

For development:

```bash
git clone https://github.com/SapCommerceTools/ha-client-core.git
cd hac-client-core
pip install -e ".[dev]"
```

## Quick start

```python
from hac_client_core import HacClient, BasicAuthHandler

# 1. Create an auth handler
auth = BasicAuthHandler("admin", "nimda")

# 2. Create the client
client = HacClient(
    base_url="https://localhost:9002",
    auth_handler=auth,
    ignore_ssl=True,           # skip certificate verification (dev only)
    session_persistence=True,  # cache sessions between runs
)

# 3. Login (or let it happen automatically on the first call)
client.login()

# 4. Execute a Groovy script
result = client.execute_groovy("return 'Hello from HAC'")
print(result.execution_result)  # "Hello from HAC"
```

## Usage

### Groovy script execution

```python
result = client.execute_groovy(
    script="return de.hybris.platform.core.Registry.applicationContext",
    commit=False,  # rollback mode (default)
)

if result.success:
    print(result.output_text)       # stdout output
    print(result.execution_result)  # return value
else:
    print(result.stacktrace_text)   # error details
```

Set `commit=True` to execute in commit mode — changes will be persisted to the database.

### FlexibleSearch queries

```python
result = client.execute_flexiblesearch(
    query="SELECT {pk}, {code} FROM {Product} WHERE {code} LIKE '%camera%'",
    max_count=50,
    locale="en",
)

if result.success:
    print(f"Columns: {result.headers}")
    print(f"Rows returned: {result.result_count}")
    for row in result.rows:
        print(row)
else:
    print(f"Query error: {result.exception}")
```

### Impex import

```python
impex = """
INSERT_UPDATE Product; code[unique=true]; name[lang=en]
; testProduct001 ; Test Product
"""

result = client.import_impex(impex, validation_mode="import_strict")

if result.success:
    print("Import completed")
else:
    print(f"Import failed: {result.error}")
```

### System update

```python
# Fetch available extensions and their parameters
update_data = client.get_update_data()

for ext in update_data.extensions_with_parameters:
    print(f"{ext.name}: {[p.name for p in ext.parameters]}")

# Execute an update with specific patches
result = client.execute_update(
    patches={"Patch_MVP": "yes"},
    create_essential_data=True,
    create_project_data=True,
)

print(f"Success: {result.success}")
print(result.log_text)
```

Poll the update log while a long-running update is in progress:

```python
import time

while True:
    log = client.get_update_log()
    print(log.log_text)
    if log.is_complete:
        break
    time.sleep(5)
```

### Session management

Sessions are cached to `~/.cache/hac-client/` by default so subsequent runs skip authentication:

```python
# Sessions are cached per (base_url, username, environment) tuple
client = HacClient(
    base_url="https://localhost:9002",
    auth_handler=auth,
    environment="local",          # tag sessions by environment
    session_persistence=True,     # enable caching (default)
)
```

Manage the session cache directly:

```python
from hac_client_core import SessionManager

mgr = SessionManager()

# List all cached sessions
for s in mgr.list_sessions():
    print(f"{s.environment}  {s.base_url}  created={s.created_at_formatted}")

# Clear all sessions
mgr.clear_all_sessions()
```

### Custom authentication

Implement `AuthHandler` to support any authentication scheme:

```python
from hac_client_core import AuthHandler
import requests

class BearerTokenAuth(AuthHandler):
    def __init__(self, token: str, username: str):
        self._token = token
        self._username = username

    def apply_auth(self, request: requests.PreparedRequest) -> requests.PreparedRequest:
        request.headers["Authorization"] = f"Bearer {self._token}"
        return request

    def get_initial_credentials(self) -> dict[str, str]:
        return {"j_username": self._username, "j_password": self._token}
```

## API reference

### `HacClient`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `base_url` | `str` | — | HAC base URL (e.g. `https://localhost:9002`) |
| `auth_handler` | `AuthHandler` | — | Authentication handler |
| `environment` | `str` | `"local"` | Environment name for session caching |
| `timeout` | `int` | `30` | HTTP timeout in seconds |
| `ignore_ssl` | `bool` | `False` | Skip SSL certificate verification |
| `session_persistence` | `bool` | `True` | Cache sessions to disk |
| `quiet` | `bool` | `False` | Suppress informational messages on stderr |

**Methods:**

| Method | Returns | Description |
|---|---|---|
| `login()` | `None` | Authenticate and establish a session |
| `execute_groovy(script, commit=False)` | `GroovyScriptResult` | Execute a Groovy script |
| `execute_flexiblesearch(query, max_count=200, locale="en")` | `FlexibleSearchResult` | Run a FlexibleSearch query |
| `import_impex(impex_content, validation_mode="import_strict")` | `ImpexResult` | Import Impex data |
| `get_update_data()` | `UpdateData` | Fetch available update extensions and parameters |
| `execute_update(...)` | `UpdateResult` | Trigger a system update |
| `get_pending_patches()` | `dict` | Fetch pending system patches |
| `get_update_log()` | `UpdateLog` | Poll the current update log |

### Result models

All result dataclasses are importable from `hac_client_core`:

| Model | Key fields |
|---|---|
| `GroovyScriptResult` | `output_text`, `execution_result`, `stacktrace_text`, `success` |
| `FlexibleSearchResult` | `headers`, `rows`, `result_count`, `exception`, `success` |
| `ImpexResult` | `success`, `output`, `error` |
| `UpdateData` | `is_initializing`, `project_datas`, `extensions_with_parameters` |
| `UpdateResult` | `success`, `log_text`, `is_finished` |
| `UpdateLog` | `log_text`, `is_complete`, `has_errors` |

### Exceptions

| Exception | Description |
|---|---|
| `HacClientError` | Base exception for all client errors |
| `HacAuthenticationError` | Authentication or session errors |

## Security considerations

- **Credentials in memory** — `BasicAuthHandler` clears its password reference on garbage collection. For stronger guarantees, implement a custom `AuthHandler` backed by a secrets manager.
- **CSRF protection** — the client automatically extracts and sends CSRF tokens on every request.
- **Session cache** — cached sessions are stored as JSON files in `~/.cache/hac-client/` with filesystem permissions of the current user. The cache contains session IDs and CSRF tokens — not passwords.
- **SSL verification** — `ignore_ssl=True` disables certificate checks. Use it only for local development with self-signed certificates.

## Development

```bash
# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Type checking
mypy src/

# Lint
ruff check src/
```

## License

[MIT](LICENSE)