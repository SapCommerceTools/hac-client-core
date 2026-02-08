# Authentication

::: hac_client_core.auth

Authentication is handled through a pluggable `AuthHandler` abstraction.

---

## AuthHandler

```python
from abc import ABC, abstractmethod

class AuthHandler(ABC):
    ...
```

Abstract base class.  Subclass this to implement custom authentication.

### Methods

#### `apply_auth()`

```python
@abstractmethod
def apply_auth(
    self,
    request: requests.PreparedRequest,
) -> requests.PreparedRequest
```

Apply authentication to an outgoing HTTP request.  Modify and return the `PreparedRequest` — e.g. set headers, cookies, or query parameters.

Called for every request the client makes.

---

#### `get_initial_credentials()`

```python
@abstractmethod
def get_initial_credentials() -> dict[str, str]
```

Return credentials for the initial Spring Security login form.

Must return a dict with at least:

- `j_username` — HAC username
- `j_password` — HAC password

---

## BasicAuthHandler

```python
from hac_client_core import BasicAuthHandler

auth = BasicAuthHandler(username="admin", password="nimda")
```

Built-in handler for standard HAC form-based login.  Marked `@final` — not intended for subclassing.

### Constructor

| Parameter | Type | Description |
|---|---|---|
| `username` | `str` | HAC username |
| `password` | `str` | HAC password |

### Security

- The password is stored as a private attribute (`_password`)
- The reference is cleared to `None` in `__del__()` when the handler is garbage-collected
- For stronger guarantees, implement a custom handler that fetches credentials on-demand from a secrets manager

### Attributes

| Attribute | Type | Description |
|---|---|---|
| `username` | `str` | The HAC username (public) |

See the [Custom authentication guide](../usage/authentication.md) for examples of writing your own handler.
