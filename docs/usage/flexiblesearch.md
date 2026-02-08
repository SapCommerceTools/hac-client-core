# FlexibleSearch queries

FlexibleSearch is SAP Commerce's query language for reading data from the type system.  The client wraps the HAC FlexibleSearch console.

## Basic usage

```python
result = client.execute_flexiblesearch(
    query="SELECT {pk}, {code} FROM {Product}",
    max_count=100,
)

print(result.headers)       # ["pk", "code"]
print(result.result_count)  # number of rows returned

for row in result.rows:
    print(row)              # ["8796093054977", "camera-001"]
```

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `query` | `str` | _(required)_ | The FlexibleSearch query |
| `max_count` | `int` | `200` | Maximum number of rows to return |
| `locale` | `str` | `"en"` | Locale used for localized attributes |

## Pagination

The HAC limits results to `max_count` rows.  To page through large result sets, combine `max_count` with `WHERE` clauses:

```python
last_pk = 0

while True:
    result = client.execute_flexiblesearch(
        query=f"SELECT {{pk}}, {{code}} FROM {{Product}} WHERE {{pk}} > {last_pk} ORDER BY {{pk}}",
        max_count=500,
    )

    if not result.rows:
        break

    for row in result.rows:
        print(row)

    last_pk = result.rows[-1][0]  # pk of the last row
```

## Error handling

Query syntax errors or runtime failures are returned in the `exception` field:

```python
result = client.execute_flexiblesearch("SELECT bad query")

if not result.success:
    print(result.exception)
    # FlexibleSearchException: could not parse query...
```

## Data analysis with pandas

FlexibleSearch results map directly to a DataFrame — the `headers` become column names and `rows` become data.  This makes it easy to analyse SAP Commerce data with the standard Python data-science stack.

### Loading results into pandas

```python
import pandas as pd
from hac_client_core import HacClient, BasicAuthHandler

auth = BasicAuthHandler("admin", "nimda")
client = HacClient(
    base_url="https://localhost:9002",
    auth_handler=auth,
    ignore_ssl=True,
)
client.login()

result = client.execute_flexiblesearch(
    query="""\
        SELECT {p.code}, {p.name}, {p.creationtime}, {s.level}
        FROM {Product AS p
            JOIN StockLevel AS s ON {s.productCode} = {p.code}}
    """,
    max_count=5000,
)

df = pd.DataFrame(result.rows, columns=result.headers)
print(df.head())
```

### Transforming and exploring

```python
# Parse timestamps and numeric columns
df["creationtime"] = pd.to_datetime(df["creationtime"])
df["level"] = pd.to_numeric(df["level"], errors="coerce")

# Products with the lowest stock
low_stock = df.nsmallest(10, "level")
print(low_stock[["code", "name", "level"]])

# Products created per month
df["month"] = df["creationtime"].dt.to_period("M")
products_per_month = df.groupby("month").size()
print(products_per_month)
```

### Visualising with matplotlib

```python
import matplotlib.pyplot as plt

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Stock level distribution
axes[0].hist(df["level"].dropna(), bins=30, edgecolor="black")
axes[0].set_title("Stock level distribution")
axes[0].set_xlabel("Stock level")
axes[0].set_ylabel("Number of products")

# Products created over time
products_per_month.plot(kind="bar", ax=axes[1])
axes[1].set_title("Products created per month")
axes[1].set_ylabel("Count")
axes[1].tick_params(axis="x", rotation=45)

plt.tight_layout()
plt.savefig("product_analysis.png", dpi=150)
plt.show()
```

!!! tip
    For larger datasets, use the [pagination pattern](#pagination) to fetch
    all rows in batches and concatenate them into a single DataFrame with
    `pd.concat()`.

## Result object

See [`FlexibleSearchResult`](../api/models.md#flexiblesearchresult) for the full field reference.

| Field | Type | Description |
|---|---|---|
| `headers` | `list[str]` | Column headers |
| `rows` | `list[list[str]]` | Result rows |
| `result_count` | `int` | Number of rows returned |
| `execution_time_ms` | `int \| None` | Server-side execution time |
| `exception` | `str \| None` | Error message if query failed |
| `success` | `bool` | _(property)_ `True` if no exception |
