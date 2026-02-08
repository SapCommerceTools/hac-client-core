# HacClient

::: hac_client_core.client

The main entry point for interacting with the SAP Commerce HAC API.

```python
from hac_client_core import HacClient, BasicAuthHandler

auth = BasicAuthHandler("admin", "nimda")
client = HacClient("https://localhost:9002", auth_handler=auth)
```

---

## Constructor

```python
HacClient(
    base_url: str,
    auth_handler: AuthHandler,
    environment: str = "local",
    timeout: int = 30,
    ignore_ssl: bool = False,
    session_persistence: bool = True,
    quiet: bool = False,
)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `base_url` | `str` | _(required)_ | HAC base URL (e.g. `https://localhost:9002`) |
| `auth_handler` | [`AuthHandler`](auth.md#authhandler) | _(required)_ | Authentication handler |
| `environment` | `str` | `"local"` | Environment name used as key for session caching |
| `timeout` | `int` | `30` | HTTP timeout in seconds for all requests |
| `ignore_ssl` | `bool` | `False` | Skip SSL certificate verification |
| `session_persistence` | `bool` | `True` | Cache sessions to `~/.cache/hac-client/` |
| `quiet` | `bool` | `False` | Suppress informational messages on stderr |

---

## Methods

### `login()`

```python
client.login() -> None
```

Authenticate with HAC and establish a session.

- Attempts to load a cached session first (if `session_persistence` is enabled)
- Validates the cached session with a lightweight GET request
- Falls back to a fresh login via Spring Security form submission
- Extracts and stores `JSESSIONID`, CSRF token, and `ROUTE` cookie

**Raises:** [`HacAuthenticationError`](exceptions.md#hacauthenticationerror) if authentication fails.

!!! note
    You don't need to call `login()` explicitly — all API methods call it
    automatically if no session exists.

---

### `execute_groovy()`

```python
client.execute_groovy(
    script: str,
    commit: bool = False,
) -> GroovyScriptResult
```

Execute a Groovy script in the HAC scripting console.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `script` | `str` | _(required)_ | Groovy source code |
| `commit` | `bool` | `False` | `True` = persist DB changes; `False` = rollback |

**Returns:** [`GroovyScriptResult`](models.md#groovyscriptresult)

**Raises:** [`HacClientError`](exceptions.md#hacclienterror), [`HacAuthenticationError`](exceptions.md#hacauthenticationerror)

---

### `execute_flexiblesearch()`

```python
client.execute_flexiblesearch(
    query: str,
    max_count: int = 200,
    locale: str = "en",
) -> FlexibleSearchResult
```

Execute a FlexibleSearch query.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `query` | `str` | _(required)_ | FlexibleSearch query string |
| `max_count` | `int` | `200` | Maximum number of result rows |
| `locale` | `str` | `"en"` | Locale for localized attribute values |

**Returns:** [`FlexibleSearchResult`](models.md#flexiblesearchresult)

**Raises:** [`HacClientError`](exceptions.md#hacclienterror), [`HacAuthenticationError`](exceptions.md#hacauthenticationerror)

---

### `import_impex()`

```python
client.import_impex(
    impex_content: str,
    validation_mode: str = "import_strict",
) -> ImpexResult
```

Import Impex data.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `impex_content` | `str` | _(required)_ | Impex content to import |
| `validation_mode` | `str` | `"import_strict"` | One of `import_strict`, `import_relaxed` |

**Returns:** [`ImpexResult`](models.md#impexresult)

**Raises:** [`HacClientError`](exceptions.md#hacclienterror), [`HacAuthenticationError`](exceptions.md#hacauthenticationerror)

---

### `get_update_data()`

```python
client.get_update_data() -> UpdateData
```

Fetch available system update extensions and their configurable parameters.

**Returns:** [`UpdateData`](models.md#updatedata)

**Raises:** [`HacClientError`](exceptions.md#hacclienterror)

---

### `execute_update()`

```python
client.execute_update(
    patches: dict[str, str] | None = None,
    drop_tables: bool = False,
    clear_hmc: bool = False,
    create_essential_data: bool = False,
    create_project_data: bool = False,
    localize_types: bool = False,
    all_parameters: dict[str, Any] | None = None,
    include_pending_patches: bool = True,
) -> UpdateResult
```

Trigger a system update.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `patches` | `dict[str, str] \| None` | `None` | Patch name → value (e.g. `{"Patch_MVP": "yes"}`) |
| `drop_tables` | `bool` | `False` | Drop all tables (**dangerous**) |
| `clear_hmc` | `bool` | `False` | Clear HMC configuration |
| `create_essential_data` | `bool` | `False` | Create essential data |
| `create_project_data` | `bool` | `False` | Create project data |
| `localize_types` | `bool` | `False` | Localize types |
| `all_parameters` | `dict \| None` | `None` | Full parameters dict (overrides `patches`) |
| `include_pending_patches` | `bool` | `True` | Auto-include required system patches |

**Returns:** [`UpdateResult`](models.md#updateresult)

**Raises:** [`HacClientError`](exceptions.md#hacclienterror)

---

### `get_pending_patches()`

```python
client.get_pending_patches() -> dict[str, list[dict[str, Any]]]
```

Fetch pending system patches that need to be included in updates.

**Returns:** Dictionary mapping patch category to list of patch dicts (each with `name`, `hash`, `required` keys).

**Raises:** [`HacClientError`](exceptions.md#hacclienterror)

---

### `get_update_log()`

```python
client.get_update_log() -> UpdateLog
```

Poll the current update/initialization log.

**Returns:** [`UpdateLog`](models.md#updatelog)

**Raises:** [`HacClientError`](exceptions.md#hacclienterror)
