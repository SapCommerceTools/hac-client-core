# Custom authentication

The client uses a pluggable `AuthHandler` abstraction so you can implement any authentication scheme.

## Built-in: BasicAuthHandler

The library ships with `BasicAuthHandler` for standard HAC form-based login (Spring Security `j_username` / `j_password`):

```python
from hac_client_core import BasicAuthHandler

auth = BasicAuthHandler("admin", "nimda")
```

This is sufficient for most SAP Commerce installations.

## Implementing a custom handler

Subclass `AuthHandler` and implement two methods:

```python
from hac_client_core import AuthHandler
import requests


class BearerTokenAuth(AuthHandler):
    """Authenticate using a pre-obtained Bearer token."""

    def __init__(self, token: str, username: str):
        self._token = token
        self._username = username

    def apply_auth(self, request: requests.PreparedRequest) -> requests.PreparedRequest:
        """Inject the Authorization header into every request."""
        request.headers["Authorization"] = f"Bearer {self._token}"
        return request

    def get_initial_credentials(self) -> dict[str, str]:
        """Provide credentials for the Spring Security login form."""
        return {
            "j_username": self._username,
            "j_password": self._token,
        }
```

### `apply_auth(request)`

Called for every outgoing HTTP request.  Modify the `PreparedRequest` to inject authentication headers, cookies, query parameters, etc.

!!! note
    Currently, HAC authentication is form-based (Spring Security), so
    `apply_auth()` is a no-op in `BasicAuthHandler`.  The method exists
    for custom schemes that need per-request credentials (e.g. Bearer
    tokens, API keys, HMAC signatures).

### `get_initial_credentials()`

Must return a `dict[str, str]` with at least `j_username` and `j_password` keys.  These are submitted to the `/hac/j_spring_security_check` endpoint during login.

## Example: secrets manager integration

```python
import boto3
from hac_client_core import AuthHandler


class AWSSecretsAuth(AuthHandler):
    """Fetch credentials from AWS Secrets Manager at login time."""

    def __init__(self, secret_name: str, region: str = "eu-central-1"):
        self._secret_name = secret_name
        self._region = region

    def apply_auth(self, request):
        return request

    def get_initial_credentials(self) -> dict[str, str]:
        client = boto3.client("secretsmanager", region_name=self._region)
        response = client.get_secret_value(SecretId=self._secret_name)
        import json
        secret = json.loads(response["SecretString"])
        return {
            "j_username": secret["username"],
            "j_password": secret["password"],
        }
```

```python
auth = AWSSecretsAuth("prod/hac-credentials")
client = HacClient("https://hac.example.com", auth_handler=auth)
```

## Security notes

- `BasicAuthHandler` clears its password reference when garbage-collected (`__del__`)
- For stronger guarantees, implement a handler that fetches credentials on-demand from a secrets manager (as shown above) so passwords are never held in memory longer than necessary
- See [Security](../security.md) for more details
