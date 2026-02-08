# Groovy script execution

The HAC Groovy console lets you run arbitrary Groovy code inside the SAP Commerce runtime.  `hac-client-core` wraps this as a single method call with typed results.

## Basic usage

```python
result = client.execute_groovy("return 'Hello'")

print(result.execution_result)  # "Hello"
print(result.output_text)       # stdout output (from println, etc.)
print(result.success)           # True
```

## Commit vs. rollback mode

By default, scripts run in **rollback mode** — any database changes made during execution are rolled back when the script finishes.  This is safe for read-only exploration.

```python
# Rollback mode (default) — changes are NOT persisted
result = client.execute_groovy(
    script="return 'safe read'",
    commit=False,
)
```

To persist changes, use **commit mode**:

```python
# Commit mode — changes ARE persisted
result = client.execute_groovy(
    script="""\
import de.hybris.platform.core.model.product.ProductModel

product = modelService.create(ProductModel)
product.code = "scripted-001"
product.catalogVersion = catalogVersionService.getCatalogVersion("Default", "Online")
modelService.save(product)
return "Created ${product.code}"
""",
    commit=True,
)
```

!!! warning
    Commit mode executes changes directly in the database.  Always test
    scripts in rollback mode first.

## Error handling

When a script throws an exception, the result contains the stacktrace:

```python
result = client.execute_groovy("throw new RuntimeException('oops')")

if not result.success:
    print(result.stacktrace_text)
    # java.lang.RuntimeException: oops
    #     at Script1.run(Script1.groovy:1)
    #     ...
```

## Execution time

The HAC returns the server-side execution time:

```python
result = client.execute_groovy("Thread.sleep(500); return 'done'")
print(f"Took {result.execution_time_ms}ms")
```

## Result object

See [`GroovyScriptResult`](../api/models.md#groovyscriptresult) for the full field reference.

| Field | Type | Description |
|---|---|---|
| `output_text` | `str` | Console output (`println` etc.) |
| `execution_result` | `str` | Return value of the script |
| `stacktrace_text` | `str \| None` | Error stacktrace if failed |
| `commit_mode` | `bool` | Whether commit mode was used |
| `execution_time_ms` | `int \| None` | Server-side execution time |
| `success` | `bool` | _(property)_ `True` if no stacktrace |
