# Getting started

## Requirements

- **Python ≥ 3.12**
- A running **SAP Commerce** instance with HAC enabled

## Installation

=== "PyPI"

    ```bash
    pip install hac-client-core
    ```

=== "Git"

    ```bash
    pip install git+https://github.com/SapCommerceTools/hac-client-core.git
    ```

=== "Development"

    ```bash
    git clone https://github.com/SapCommerceTools/hac-client-core.git
    cd ha-client-core
    pip install -e ".[dev]"
    ```

## Your first script

### 1. Create an authentication handler

```python
from hac_client_core import BasicAuthHandler

auth = BasicAuthHandler("admin", "nimda")
```

### 2. Create the client

```python
from hac_client_core import HacClient

client = HacClient(
    base_url="https://localhost:9002",
    auth_handler=auth,
    ignore_ssl=True,           # skip certificate verification (dev only)
    session_persistence=True,  # cache sessions between runs
)
```

### 3. Login

```python
client.login()
```

!!! tip
    You can skip the explicit `login()` call — the client authenticates
    automatically on the first API call.

### 4. Execute a Groovy script

```python
result = client.execute_groovy("return 'Hello from HAC'")
print(result.execution_result)  # "Hello from HAC"
```

### 5. Run a FlexibleSearch query

```python
result = client.execute_flexiblesearch(
    "SELECT {pk}, {code} FROM {Product}",
    max_count=10,
)

for row in result.rows:
    print(row)
```

### 6. Import Impex data

```python
impex = """\
INSERT_UPDATE Product; code[unique=true]; name[lang=en]
; testProduct001 ; Test Product
"""

result = client.import_impex(impex)
print("OK" if result.success else result.error)
```

## What's next?

- See the [Usage guides](usage/groovy.md) for detailed examples of each operation
- Check the [API reference](api/client.md) for the full interface
- Read the [Security](security.md) page before deploying to production
