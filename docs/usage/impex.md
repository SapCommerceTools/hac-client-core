# Impex import

Impex is SAP Commerce's CSV-like format for importing and exporting data.  The client wraps the HAC Impex console for import operations.

## Basic usage

```python
impex = """\
INSERT_UPDATE Product; code[unique=true]; name[lang=en]
; testProduct001 ; Test Product
; testProduct002 ; Another Product
"""

result = client.import_impex(impex)

if result.success:
    print("Import completed successfully")
else:
    print(f"Import failed: {result.error}")
```

## Validation modes

The `validation_mode` parameter controls how strictly the Impex is validated:

```python
# Strict validation (default) — fail on any error
result = client.import_impex(impex, validation_mode="import_strict")

# Relaxed validation — skip invalid lines, import the rest
result = client.import_impex(impex, validation_mode="import_relaxed")
```

Available modes:

| Mode | Description |
|---|---|
| `import_strict` | Fail on any validation error (default) |
| `import_relaxed` | Skip invalid lines, import valid ones |

## Multi-line Impex

Python triple-quoted strings work well for multi-line Impex content:

```python
impex = """\
INSERT_UPDATE Product; code[unique=true]; name[lang=en]; description[lang=en]
; prod-001 ; Camera         ; A digital camera
; prod-002 ; Lens           ; A telephoto lens

INSERT_UPDATE Category; code[unique=true]; name[lang=en]
; cameras ; Cameras
; lenses  ; Lenses
"""

result = client.import_impex(impex)
```

!!! tip
    For large Impex imports, consider increasing the client timeout:

    ```python
    client = HacClient(
        base_url="https://localhost:9002",
        auth_handler=auth,
        timeout=120,  # 2 minutes
    )
    ```

## Result object

See [`ImpexResult`](../api/models.md#impexresult) for the full field reference.

| Field | Type | Description |
|---|---|---|
| `success` | `bool` | Whether the import succeeded |
| `output` | `str` | Output text from the operation |
| `error` | `str \| None` | Error message if failed |
| `validation_errors` | `list[str]` | List of individual validation errors |
