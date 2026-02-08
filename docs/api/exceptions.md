# Exceptions

All exceptions raised by the library are subclasses of `HacClientError`.

```python
from hac_client_core import HacClientError, HacAuthenticationError
```

---

## Exception hierarchy

```
Exception
└── HacClientError
    └── HacAuthenticationError
```

---

## HacClientError

```python
class HacClientError(Exception):
    ...
```

Base exception for all client errors.  Catch this to handle any error from the library:

```python
from hac_client_core import HacClientError

try:
    result = client.execute_groovy("return 1")
except HacClientError as e:
    print(f"HAC operation failed: {e}")
```

Raised when:

- An HTTP request fails (network error, timeout, unexpected status code)
- The HAC response cannot be parsed (invalid JSON, missing fields)

---

## HacAuthenticationError

```python
@final
class HacAuthenticationError(HacClientError):
    ...
```

Authentication or session error.  This is a subclass of `HacClientError`, so catching `HacClientError` also catches authentication errors.

To handle authentication errors specifically:

```python
from hac_client_core import HacAuthenticationError, HacClientError

try:
    client.login()
except HacAuthenticationError:
    print("Login failed — check credentials")
except HacClientError:
    print("Other HAC error")
```

Raised when:

- Login credentials are invalid
- CSRF token cannot be extracted from the login page
- Session cannot be established (missing session ID or CSRF token)
- A request returns HTTP 401, 403, or 405 (session expired)
- A network error occurs during the authentication flow
