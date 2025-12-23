# HAC Client Core

HTTP client library for SAP Commerce HAC (Hybris Administration Console) API.

## Overview

This library provides programmatic access to core SAP Commerce HAC operations:

- **Groovy script execution** with commit mode support
- **FlexibleSearch queries** with result pagination
- **Impex import/export** operations
- **Session management** with caching and CSRF protection
- **Pluggable authentication** (Basic Auth, extensible for OAuth, etc.)

Higher-level features like media management and orchestrated operations belong in the administration layer.

## Features

### Authentication Abstraction

The client supports pluggable authentication methods through an interceptor pattern:

```python
from hac_client_core.client import HacClient
from hac_client_core.auth import BasicAuthHandler

# Basic authentication
auth = BasicAuthHandler("admin", "nimda")
client = HacClient(
    base_url="https://localhost:9002",
    auth_handler=auth
)

# Execute operations
result = client.execute_groovy("return 'Hello World'")
```

### Session Management

Automatic session management with CSRF token handling and optional caching:

```python
client = HacClient(
    base_url="https://localhost:9002",
    auth_handler=auth,
    session_persistence=True  # Cache sessions between runs
)
```

### Script Execution

```python
# Execute Groovy script
result = client.execute_groovy(
    script="return de.hybris.platform.core.Registry.applicationContext",
    commit=False
)

print(result.output_text)  # Script output
print(result.execution_result)  # Return value
```

### FlexibleSearch Queries

```python
# Execute FlexibleSearch
result = client.execute_flexiblesearch(
    query="SELECT {pk} FROM {Product}",
    max_count=100,
    locale="en"
)

for row in result.rows:
    print(row)
```

## Architecture

### Auth Abstraction

Authentication is handled through the `AuthHandler` abstract base class:

- `BasicAuthHandler`: HTTP Basic Authentication
- Extensible for OAuth, JWT, API keys, etc.

### Interceptor Pattern

Authentication is applied via request interceptors, keeping the core client auth-agnostic.

## Design Principles

- **Pure Python**: No CLI concerns, no external tools
- **Type-safe**: Full type hints
- **Testable**: Mockable HTTP layer
- **Extensible**: Pluggable auth, custom interceptors

