# Result models

::: hac_client_core.models

All result types are plain Python [`dataclasses`](https://docs.python.org/3/library/dataclasses.html) with no external dependencies.  They can be compared, serialised, and used freely in tests.

```python
from hac_client_core import GroovyScriptResult, FlexibleSearchResult, ImpexResult
```

---

## GroovyScriptResult

Returned by [`HacClient.execute_groovy()`](client.md#execute_groovy).

### Fields

| Field | Type | Default | Description |
|---|---|---|---|
| `output_text` | `str` | _(required)_ | Console output (`println` etc.) |
| `execution_result` | `str` | _(required)_ | Return value of the script |
| `stacktrace_text` | `str \| None` | `None` | Error stacktrace if the script failed |
| `commit_mode` | `bool` | `False` | Whether the script ran in commit mode |
| `execution_time_ms` | `int \| None` | `None` | Server-side execution time in milliseconds |

### Properties

| Property | Type | Description |
|---|---|---|
| `success` | `bool` | `True` if `stacktrace_text` is `None` or empty |

---

## FlexibleSearchResult

Returned by [`HacClient.execute_flexiblesearch()`](client.md#execute_flexiblesearch).

### Fields

| Field | Type | Default | Description |
|---|---|---|---|
| `headers` | `list[str]` | _(required)_ | Column headers |
| `rows` | `list[list[str]]` | _(required)_ | Result rows |
| `result_count` | `int` | _(required)_ | Number of results returned |
| `execution_time_ms` | `int \| None` | `None` | Server-side execution time in milliseconds |
| `exception` | `str \| None` | `None` | Error message if the query failed |

### Properties

| Property | Type | Description |
|---|---|---|
| `success` | `bool` | `True` if `exception` is `None` |

---

## ImpexResult

Returned by [`HacClient.import_impex()`](client.md#import_impex).

### Fields

| Field | Type | Default | Description |
|---|---|---|---|
| `success` | `bool` | _(required)_ | Whether the import succeeded |
| `output` | `str` | _(required)_ | Output text from the operation |
| `error` | `str \| None` | `None` | Error message if failed |
| `validation_errors` | `list[str]` | `[]` | List of individual validation errors |

---

## SessionInfo

Internal session state held by `HacClient`.

### Fields

| Field | Type | Default | Description |
|---|---|---|---|
| `session_id` | `str` | _(required)_ | `JSESSIONID` |
| `csrf_token` | `str` | _(required)_ | CSRF token for POST requests |
| `route_cookie` | `str \| None` | `None` | `ROUTE` cookie for load balancer affinity |
| `is_authenticated` | `bool` | `False` | Whether the session is authenticated |

---

## UpdateParameter

A configurable parameter for a project data extension.

### Fields

| Field | Type | Default | Description |
|---|---|---|---|
| `name` | `str` | _(required)_ | Parameter name (e.g. `Patch_MVP`) |
| `label` | `str` | _(required)_ | Human-readable label |
| `values` | `dict[str, bool]` | _(required)_ | Available values and their selected state |
| `legacy` | `bool` | `False` | Whether this is a legacy parameter |
| `multi_select` | `bool` | `False` | Whether multiple values can be selected |
| `default` | `str \| None` | `None` | Default value |

### Properties

| Property | Type | Description |
|---|---|---|
| `selected_value` | `str \| None` | The currently selected value |
| `available_values` | `list[str]` | List of all available values |

---

## ProjectData

Information about a project data extension.

### Fields

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Extension name (e.g. `cchpatches`) |
| `description` | `str \| None` | Extension description |
| `parameters` | `list[UpdateParameter]` | Configurable parameters |

### Properties

| Property | Type | Description |
|---|---|---|
| `has_parameters` | `bool` | Whether the extension has any parameters |

---

## UpdateData

Returned by [`HacClient.get_update_data()`](client.md#get_update_data).

### Fields

| Field | Type | Description |
|---|---|---|
| `is_initializing` | `bool` | Whether an initialization is currently in progress |
| `project_datas` | `list[ProjectData]` | Available project data extensions |

### Properties

| Property | Type | Description |
|---|---|---|
| `extensions_with_parameters` | `list[ProjectData]` | Extensions that have configurable parameters |

### Methods

#### `get_extension(name: str) -> ProjectData | None`

Look up a specific extension by name.

#### `get_patches_extension() -> ProjectData | None`

Find the patches extension.  Prefers project-specific names with parameters (e.g. `cchpatches`) over generic `patches`.

---

## UpdateResult

Returned by [`HacClient.execute_update()`](client.md#execute_update).

### Fields

| Field | Type | Description |
|---|---|---|
| `success` | `bool` | Whether the update succeeded |
| `log_html` | `str` | Raw HTML log content |

### Properties

| Property | Type | Description |
|---|---|---|
| `log_text` | `str` | Plain-text version of the log (HTML tags stripped) |
| `is_finished` | `bool` | Whether the log indicates the update is finished |

---

## UpdateLog

Returned by [`HacClient.get_update_log()`](client.md#get_update_log).

### Fields

| Field | Type | Description |
|---|---|---|
| `log_html` | `str` | Raw HTML log content |

### Properties

| Property | Type | Description |
|---|---|---|
| `log_text` | `str` | Plain-text version of the log |
| `is_complete` | `bool` | Whether the update appears to be complete |
| `has_errors` | `bool` | Whether the log contains error indicators |
