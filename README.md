# antonlytics

Official Python SDK for the [Antonlytics](https://antonlytics.com) Knowledge Graph API.

[![PyPI](https://img.shields.io/pypi/v/antonlytics)](https://pypi.org/project/antonlytics/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

---

## Install

```bash
pip install antonlytics
```

---

## Quick Start

```python
from antonlytics import Antonlytics, Triplet, EntityRef

anto = Antonlytics(api_key="anto_live_xxx")

# Ingest a relationship
anto.ingest.track(
    project_id="proj_abc",
    triplets=Triplet(
        subject=EntityRef("Customer", id="c1", properties={"name": "Alice", "country": "USA"}),
        predicate="PURCHASED",
        object=EntityRef("Product", id="p1", properties={"title": "Laptop Pro", "price": 999}),
    ),
)

# Query the graph
result = (
    anto.query.build("proj_abc")
    .select("Customer", alias="c1")
        .properties("name", "email", "country")
        .eq("country", "USA")
        .gte("age", 18)
    .done()
    .order_by("age", direction="desc")
    .limit(50)
    .run()
)
for row in result:
    print(row["name"], row["country"])
```

---

## Configuration

```python
anto = Antonlytics(
    api_key="anto_live_...",           # required — from app.antonlytics.com → API Keys
    base_url="https://api.antonlytics.com",  # optional, default shown
    timeout=30.0,                      # seconds, default 30
    max_retries=2,                     # auto-retry 5xx / network errors
    debug=False,                       # print HTTP calls to stdout
)
```

Use as a **context manager** to ensure the connection pool is closed:

```python
with Antonlytics(api_key="anto_live_xxx") as anto:
    projects = anto.projects.list()
```

---

## Ingestion

All data enters the knowledge graph as **triplets**: `subject –[predicate]→ object`.

### `anto.ingest.track()` ← recommended

Ingest and automatically poll if async. Transparent for both sync and async batches.

```python
result = anto.ingest.track(
    "proj_abc",
    triplets=[
        Triplet(
            subject=EntityRef("Customer", id="c1", properties={"name": "Alice"}),
            predicate="PURCHASED",
            object=EntityRef("Product", id="p1", properties={"title": "Laptop"}),
            relationship_properties={"quantity": 2},
        ),
    ],
    interval=1.0,    # poll every 1s for async batches
    timeout=60.0,    # give up after 60s
    on_status=lambda event: print(f"Status: {event.status}"),
)
```

Batches **≤ 100** → processed synchronously, full results returned immediately.
Batches **> 100** → queued, auto-polled until done.

### `anto.ingest.batch()` — large datasets

```python
anto.ingest.batch(
    "proj_abc",
    all_my_triplets,          # any size
    chunk_size=200,           # triplets per request
    on_chunk=lambda i, n, r: print(f"Chunk {i}/{n}"),
)
```

### `anto.ingest.poll()` — manual async polling

```python
result = anto.ingest.send("proj_abc", triplets)
if result.is_async:
    event = anto.ingest.poll(
        result.event_id,
        timeout=120.0,
        on_status=lambda e: print(e.status),
    )
```

---

## Query Builder

```python
result = (
    anto.query.build("proj_abc")

    # First entity node
    .select("Customer", alias="c1")
        .properties("name", "email", "country", "age")
        .eq("country", "USA")
        .gte("age", 21)
        .relates_to("PURCHASED", "p1")   # join to product node below
    .done()

    # Second entity node (joined via PURCHASED)
    .select("Product", alias="p1")
        .properties("title", "price", "category")
        .lte("price", 500)
    .done()

    .order_by("age", direction="desc")
    .limit(100)
    .name("US adults buying affordable products")
    .run()
)

print(f"{result.total} rows in {result.execution_ms}ms")
for row in result:
    print(row)
```

**Filter operators:** `eq` · `neq` · `contains` · `starts_with` · `ends_with` · `gt` · `gte` · `lt` · `lte`

### Raw query payload

```python
result = anto.query.execute("proj_abc", {
    "entities": [{"alias": "c1", "type": "Customer",
                  "filters": [{"property": "country", "operator": "eq", "value": "USA"}]}],
    "limit": 10,
})
```

### Ontology tree

```python
tree = anto.query.ontology("proj_abc")
# { "Customer": EntityTypeDef(properties=[...], relationships=[...]), ... }
for name, defn in tree.items():
    print(name, [p.name for p in defn.properties])
```

---

## Dashboard

```python
m = anto.dashboard.metrics("proj_abc")

print(m.summary.events_tracked)
print(m.summary.active_entities)
print(m.summary.total_relationships)

# Chart data — ready to pass to matplotlib, plotly, recharts, etc.
print(m.event_volume.data)          # [{"date": "2026-04-01", "count": 42}, ...]
print(m.entity_distribution.data)   # [{"name": "Customer", "value": 1200}, ...]
print(m.relationship_growth.data)   # [{"date": "...", "new": 40, "cumulative": 400}, ...]
print(m.top_ontology_queries)       # [{"name": "US customers", "count": 18}, ...]
```

---

## Projects

```python
projects = anto.projects.list()
project  = anto.projects.get("proj_abc")
created  = anto.projects.create(name="My Graph", team_id="team-uuid")
stats    = anto.projects.stats("proj_abc")
```

---

## Async Client

```python
import asyncio
from antonlytics import AsyncAntonlytics, Triplet, EntityRef

async def main():
    async with AsyncAntonlytics(api_key="anto_live_xxx") as anto:
        # Parallel API calls
        ontology, metrics, projects = await asyncio.gather(
            anto.query.ontology("proj_abc"),
            anto.dashboard.metrics("proj_abc"),
            anto.projects.list(),
        )

        # Fluent query
        result = await (
            anto.query.build("proj_abc")
            .select("Customer").eq("country", "USA").done()
            .limit(20)
            .run()
        )
        for row in result:
            print(row)

asyncio.run(main())
```

---

## Error Handling

```python
from antonlytics import (
    AntoError, AuthenticationError, PlanLimitError,
    NotFoundError, RateLimitError, NetworkError, TimeoutError,
)

try:
    anto.ingest.track(...)
except PlanLimitError as e:
    print(f"Plan limit hit: {e.message}")
    # Redirect user to app.antonlytics.com/billing
except AuthenticationError:
    print("API key is invalid or revoked")
except AntoError as e:
    print(f"[{e.code}] HTTP {e.status}: {e.message}")
    print(e.details)
```

| Exception | HTTP | When |
|---|---|---|
| `AuthenticationError` | 401 | Invalid API key |
| `PermissionError` | 403 | Key lacks permission |
| `NotFoundError` | 404 | Project/resource not found |
| `PlanLimitError` | 402 | Event or key quota exhausted |
| `ValidationError` | 400/422 | Bad request payload |
| `RateLimitError` | 429 | Too many requests |
| `ServerError` | 5xx | Backend error |
| `NetworkError` | — | DNS / connection failure |
| `TimeoutError` | — | Request exceeded timeout |
| `IngestionFailedError` | — | Async job failed |
| `PollTimeoutError` | — | Async job didn't finish in time |
| `InvalidConfigError` | — | Bad client configuration |

---

## CLI

```bash
# Set your API key
export ANTO_API_KEY=anto_live_xxx

anto projects
anto stats      <project-id>
anto ontology   <project-id>
anto ingest     <project-id> ./triplets.json
anto query      <project-id> ./query.json
anto dashboard  <project-id>
anto poll       <event-id>

# Environment
ANTO_BASE_URL=http://localhost:8000   # self-hosted
ANTO_DEBUG=1                          # log HTTP calls
```

---

## Django / Flask Integration

```python
# settings.py (Django) or app.py (Flask)
from antonlytics import Antonlytics

anto = Antonlytics(
    api_key=os.environ["ANTONLYTICS_API_KEY"],
    base_url=os.environ.get("ANTONLYTICS_BASE_URL", "https://api.antonlytics.com"),
)
```

---

## Development

```bash
pip install -e ".[dev]"
pytest
mypy antonlytics
ruff check antonlytics
```

---

## Publishing to PyPI

```bash
pip install build twine
python -m build
twine upload dist/*
```

---

## License

MIT © Antonlytics
