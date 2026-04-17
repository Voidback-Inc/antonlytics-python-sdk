"""
examples/basic.py — Antonlytics Python SDK complete example.

Run:
    ANTO_API_KEY=anto_live_xxx ANTO_PROJECT_ID=proj_abc python examples/basic.py
"""
import os
from antonlytics import (
    Antonlytics, Triplet, EntityRef,
    AntoError, PlanLimitError,
)
    Antonlytics, Triplet, EntityRef,
    AntoError, PlanLimitError, issubclass,
)

PROJECT_ID = os.environ.get("ANTO_PROJECT_ID", "YOUR_PROJECT_ID")

anto = Antonlytics(
    api_key=os.environ.get("ANTO_API_KEY", "anto_live_xxx"),
    base_url=os.environ.get("ANTO_BASE_URL", "http://localhost:8000"),
    debug=False,
)

def section(title: str) -> None:
    print(f"\n{'━' * 50}")
    print(f"  {title}")
    print('━' * 50)


# ── 1. List projects ──────────────────────────────────────────────────────────
section("1. List Projects")
projects = anto.projects.list()
print(f"  Found {len(projects)} project(s)")
for p in projects:
    print(f"  • {p.id}  {p.name}")


# ── 2. Ingest triplets ────────────────────────────────────────────────────────
section("2. Ingest Triplets")
result = anto.ingest.track(
    PROJECT_ID,
    triplets=[
        Triplet(
            subject=EntityRef("Customer", id="cust_1",
                              properties={"name": "Alice Johnson", "country": "USA", "age": 32}),
            predicate="PURCHASED",
            object=EntityRef("Product", id="prod_laptop",
                             properties={"title": "Laptop Pro", "price": 1299, "category": "Electronics"}),
            relationship_properties={"quantity": 1, "date": "2026-04-15"},
        ),
        Triplet(
            subject=EntityRef("Customer", id="cust_2",
                              properties={"name": "Bob Smith", "country": "UK", "age": 27}),
            predicate="PURCHASED",
            object=EntityRef("Product", id="prod_phone",
                             properties={"title": "Smartphone X", "price": 799, "category": "Mobile"}),
        ),
        Triplet(
            subject=EntityRef("Product", id="prod_laptop"),
            predicate="BELONGS_TO",
            object=EntityRef("Category", id="cat_tech",
                             properties={"name": "Technology", "slug": "technology"}),
        ),
    ],
    on_status=lambda e: print(f"  Async status: {e.status}"),
)
if hasattr(result, "results") and result.results:
    r = result.results
    print(f"  Entities created:      {r.created_entities}")
    print(f"  Entities updated:      {r.updated_entities}")
    print(f"  Relationships created: {r.created_relationships}")


# ── 3. Ontology ───────────────────────────────────────────────────────────────
section("3. Ontology Tree")
ontology = anto.query.ontology(PROJECT_ID)
for type_name, defn in ontology.items():
    props = ", ".join(p.name for p in defn.properties)
    rels  = ", ".join(f"{r.name}→{r.target}" for r in defn.relationships)
    print(f"  {type_name:<16}  props: [{props}]" + (f"  rels: [{rels}]" if rels else ""))


# ── 4. Fluent query ───────────────────────────────────────────────────────────
section("4. Fluent Query Builder")
result = (
    anto.query.build(PROJECT_ID)
    .select("Customer", alias="c1")
        .properties("name", "email", "country", "age")
        .eq("country", "USA")
        .gte("age", 18)
    .done()
    .order_by("age", direction="desc")
    .limit(10)
    .name("US adult customers")
    .run()
)
print(f"  {result.total} rows in {result.execution_ms}ms")
for row in list(result)[:5]:
    print(f"  {row}")


# ── 5. Relationship join query ────────────────────────────────────────────────
section("5. Join Query — Customer → Product")
join_result = (
    anto.query.build(PROJECT_ID)
    .select("Customer", alias="c1")
        .properties("name", "country")
        .relates_to("PURCHASED", "p1")
    .done()
    .select("Product", alias="p1")
        .properties("title", "price")
        .lte("price", 1000)
    .done()
    .limit(5)
    .run()
)
print(f"  {join_result.total} rows")
for row in join_result:
    print(f"  {row}")


# ── 6. Dashboard metrics ──────────────────────────────────────────────────────
section("6. Dashboard Metrics")
metrics = anto.dashboard.metrics(PROJECT_ID)
print(f"  Events tracked:      {metrics.summary.events_tracked:,}")
print(f"  Active entities:     {metrics.summary.active_entities:,}")
print(f"  Total relationships: {metrics.summary.total_relationships:,}")
print(f"  Query usage:         {metrics.summary.query_usage:,}")
print(f"  Entity distribution: {metrics.entity_distribution.data}")
print(f"  Recent events:       {[(e.status, e.triplets_count) for e in metrics.recent_events]}")


# ── 7. Large batch ingest ─────────────────────────────────────────────────────
section("7. Batch Ingest (50 triplets, chunks of 20)")
batch_triplets = [
    Triplet(
        subject=EntityRef("Customer", id=f"batch_{i}",
                          properties={"name": f"User {i}", "country": "USA" if i % 2 == 0 else "UK"}),
        predicate="VIEWED",
        object=EntityRef("Page", id=f"page_{i % 10}",
                         properties={"url": f"/product/{i % 10}"}),
    )
    for i in range(50)
]
anto.ingest.batch(
    PROJECT_ID,
    batch_triplets,
    chunk_size=20,
    on_chunk=lambda i, n, r: print(f"  Chunk {i}/{n} → {getattr(r, 'results', None) and r.results.created_entities or '?'} entities"),
)


# ── 8. Graph stats ────────────────────────────────────────────────────────────
section("8. Graph Stats")
stats = anto.projects.stats(PROJECT_ID)
print(f"  Entity types:          {stats.entity_types}")
print(f"  Relationship types:    {stats.relationship_types}")
print(f"  Total entities:        {stats.total_entities:,}")
print(f"  Total relationships:   {stats.total_relationships:,}")

print("\n✓ All examples completed.\n")
anto.close()
