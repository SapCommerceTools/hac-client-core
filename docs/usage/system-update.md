# System update

The client can trigger SAP Commerce system updates (the equivalent of clicking "Update" in HAC → Platform → Update), select which patches and parameters to include, and poll the update log.

## Fetch available extensions

Before running an update, inspect available extensions and their configurable parameters:

```python
update_data = client.get_update_data()

# Check if an update is already running
if update_data.is_initializing:
    print("An update is already in progress!")

# List extensions with parameters
for ext in update_data.extensions_with_parameters:
    print(f"\n{ext.name}:")
    for param in ext.parameters:
        print(f"  {param.name}: {param.available_values} (selected: {param.selected_value})")
```

## Find the patches extension

The `get_patches_extension()` helper locates the project-specific patches extension:

```python
patches_ext = update_data.get_patches_extension()
if patches_ext:
    for param in patches_ext.parameters:
        print(f"{param.name}: {param.available_values}")
```

## Execute an update

```python
result = client.execute_update(
    patches={"Patch_MVP": "yes"},
    create_essential_data=True,
    create_project_data=True,
)

print(f"Success: {result.success}")
print(result.log_text)
```

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `patches` | `dict[str, str] \| None` | `None` | Patch name → value mappings |
| `drop_tables` | `bool` | `False` | Drop all tables (**dangerous**) |
| `clear_hmc` | `bool` | `False` | Clear HMC configuration |
| `create_essential_data` | `bool` | `False` | Create essential data |
| `create_project_data` | `bool` | `False` | Create project data |
| `localize_types` | `bool` | `False` | Localize types |
| `all_parameters` | `dict \| None` | `None` | Full parameters dict (overrides `patches`) |
| `include_pending_patches` | `bool` | `True` | Auto-include required system patches |

!!! danger
    Setting `drop_tables=True` will **destroy all data**.  This is
    irreversible.

## Poll update progress

System updates can take minutes.  Poll the update log to track progress:

```python
import time

while True:
    log = client.get_update_log()
    print(log.log_text[-200:])  # last 200 chars

    if log.is_complete:
        if log.has_errors:
            print("Update completed with errors!")
        else:
            print("Update completed successfully!")
        break

    time.sleep(5)
```

## Get pending patches

Fetch system patches that are pending (e.g. validation patches):

```python
pending = client.get_pending_patches()

for category, patch_list in pending.items():
    print(f"\n{category}:")
    for patch in patch_list:
        required = "required" if patch.get("required") else "optional"
        print(f"  {patch.get('name', 'unnamed')} ({required})")
```

!!! note
    When `include_pending_patches=True` (the default), `execute_update()`
    automatically includes required pending patches.  You normally don't
    need to call `get_pending_patches()` manually.

## Result objects

- [`UpdateData`](../api/models.md#updatedata) — available extensions and parameters
- [`UpdateResult`](../api/models.md#updateresult) — update execution result
- [`UpdateLog`](../api/models.md#updatelog) — progress log for polling
