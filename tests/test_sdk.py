"""
Antonlytics Python SDK — Test Suite
"""
from __future__ import annotations

import pytest
import httpx
from pytest_httpx import HTTPXMock

from antonlytics import (
    Antonlytics, AsyncAntonlytics,
    Triplet, EntityRef,
    AntoError, AuthenticationError, NotFoundError,
    PlanLimitError, ValidationError, InvalidConfigError,
)
from antonlytics.models import IngestResponse, QueryResult, Project, GraphStats


# ── Fixtures ──────────────────────────────────────────────────────────────────

BASE = "http://testserver"

@pytest.fixture
def anto():
    return Antonlytics(
        api_key="anto_live_testkey123",
        base_url=BASE,
        timeout=5.0,
        max_retries=0,
    )

@pytest.fixture
def async_anto():
    return AsyncAntonlytics(
        api_key="anto_live_testkey123",
        base_url=BASE,
        timeout=5.0,
        max_retries=0,
    )

def triplet() -> Triplet:
    return Triplet(
        subject=EntityRef("Customer", id="c1", properties={"name": "Alice", "country": "USA"}),
        predicate="PURCHASED",
        object=EntityRef("Product", id="p1", properties={"title": "Laptop Pro", "price": 999}),
        relationship_properties={"quantity": 1},
    )

# ── Constructor validation ────────────────────────────────────────────────────

class TestConstructor:
    def test_raises_on_empty_api_key(self):
        with pytest.raises(InvalidConfigError, match="apiKey is required"):
            Antonlytics(api_key="")

    def test_raises_on_wrong_prefix(self):
        with pytest.raises(InvalidConfigError, match="anto_live_"):
            Antonlytics(api_key="sk_test_wrongformat")

    def test_creates_successfully(self):
        anto = Antonlytics(api_key="anto_live_testkey")
        assert anto is not None
        assert anto.ingest is not None
        assert anto.query is not None
        assert anto.projects is not None
        assert anto.dashboard is not None

    def test_context_manager(self):
        with Antonlytics(api_key="anto_live_testkey") as anto:
            assert anto is not None

# ── Models ────────────────────────────────────────────────────────────────────

class TestModels:
    def test_triplet_to_dict(self):
        t = triplet()
        d = t.to_dict()
        assert d["predicate"] == "PURCHASED"
        assert d["subject"]["type"] == "Customer"
        assert d["subject"]["id"] == "c1"
        assert d["subject"]["properties"]["name"] == "Alice"
        assert d["object"]["type"] == "Product"
        assert d["relationship_properties"]["quantity"] == 1

    def test_entity_ref_to_dict_no_id(self):
        e = EntityRef("Order")
        d = e.to_dict()
        assert d == {"type": "Order"}

    def test_entity_ref_to_dict_with_properties(self):
        e = EntityRef("Customer", id="c1", properties={"age": 30})
        d = e.to_dict()
        assert d["id"] == "c1"
        assert d["properties"]["age"] == 30

    def test_query_result_iteration(self):
        result = QueryResult(
            success=True,
            rows=[{"name": "Alice"}, {"name": "Bob"}],
            total=2,
            columns=["name"],
            execution_ms=5,
        )
        names = [r["name"] for r in result]
        assert names == ["Alice", "Bob"]
        assert len(result) == 2

    def test_query_result_from_dict(self):
        d = {"success": True, "rows": [{"x": 1}], "total": 1, "columns": ["x"], "execution_ms": 10}
        r = QueryResult.from_dict(d)
        assert r.total == 1
        assert r.execution_ms == 10
        assert r.rows[0]["x"] == 1

# ── Exceptions ────────────────────────────────────────────────────────────────

class TestExceptions:
    def test_anto_error_attributes(self):
        e = AntoError("something went wrong", status=500, code="SERVER_ERROR")
        assert e.status == 500
        assert e.code == "SERVER_ERROR"
        assert str(e) == "something went wrong"

    def test_to_dict(self):
        e = PlanLimitError("limit reached", details={"used": 5001})
        d = e.to_dict()
        assert d["code"] == "PLAN_LIMIT_REACHED"
        assert d["status"] == 402
        assert d["details"]["used"] == 5001

    def test_error_hierarchy(self):
        assert issubclass(AuthenticationError, AntoError)
        assert issubclass(PlanLimitError, AntoError)
        assert issubclass(NotFoundError, AntoError)

# ── Ingestion (sync) ──────────────────────────────────────────────────────────

class TestIngest:
    def test_send_single_triplet(self, anto: Antonlytics, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE}/api/v1/ingest/",
            json={
                "success": True, "event_id": "evt_1", "async": False,
                "results": {"created_entities": 2, "updated_entities": 0,
                            "created_relationships": 1, "errors": []},
            },
            status_code=201,
        )
        result = anto.ingest.send("proj_1", triplet())
        assert result.success is True
        assert result.event_id == "evt_1"
        assert result.is_async is False
        assert result.results is not None
        assert result.results.created_entities == 2

        req = httpx_mock.get_request()
        body = __import__("json").loads(req.content)
        assert body["project_id"] == "proj_1"
        assert len(body["triplets"]) == 1
        assert body["triplets"][0]["predicate"] == "PURCHASED"

    def test_send_validates_empty_list(self, anto: Antonlytics):
        with pytest.raises(ValueError, match="At least one triplet"):
            anto.ingest.send("proj_1", [])

    def test_track_sync_returns_ingest_response(self, anto: Antonlytics, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            method="POST", url=f"{BASE}/api/v1/ingest/",
            json={"success": True, "event_id": "e1", "async": False,
                  "results": {"created_entities": 1, "updated_entities": 0,
                              "created_relationships": 0, "errors": []}},
            status_code=201,
        )
        result = anto.ingest.track("proj_1", triplet())
        assert isinstance(result, IngestResponse)

    def test_raises_plan_limit_error_on_402(self, anto: Antonlytics, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            method="POST", url=f"{BASE}/api/v1/ingest/",
            json={"code": "PLAN_LIMIT_REACHED", "detail": "5000 event limit reached."},
            status_code=402,
        )
        with pytest.raises(PlanLimitError):
            anto.ingest.send("proj_1", triplet())

    def test_raises_auth_error_on_401(self, anto: Antonlytics, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            method="POST", url=f"{BASE}/api/v1/ingest/",
            json={"detail": "Invalid API key"}, status_code=401,
        )
        with pytest.raises(AuthenticationError):
            anto.ingest.send("proj_1", triplet())

    def test_poll_resolves_done(self, anto: Antonlytics, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url=f"{BASE}/api/v1/ingest/events/evt_1/",
            json={"success": True, "event": {
                "id": "evt_1", "status": "processing",
                "triplets_count": 5, "processed_at": None, "created_at": "",
            }},
        )
        httpx_mock.add_response(
            url=f"{BASE}/api/v1/ingest/events/evt_1/",
            json={"success": True, "event": {
                "id": "evt_1", "status": "done",
                "triplets_count": 5, "processed_at": "2026-04-15", "created_at": "",
            }},
        )
        statuses = []
        event = anto.ingest.poll("evt_1", interval=0, on_status=lambda e: statuses.append(e.status))
        assert event.status == "done"
        assert statuses == ["processing", "done"]

    def test_batch_splits_into_chunks(self, anto: Antonlytics, httpx_mock: HTTPXMock):
        for _ in range(3):
            httpx_mock.add_response(
                method="POST", url=f"{BASE}/api/v1/ingest/",
                json={"success": True, "event_id": "e", "async": False,
                      "results": {"created_entities": 3, "updated_entities": 0,
                                  "created_relationships": 3, "errors": []}},
                status_code=201,
            )
        t = triplet()
        chunks_seen = []
        anto.ingest.batch(
            "proj_1", [t] * 7, chunk_size=3,
            on_chunk=lambda i, n, _: chunks_seen.append((i, n)),
        )
        assert chunks_seen == [(1, 3), (2, 3), (3, 3)]
        assert len(httpx_mock.get_requests()) == 3

# ── Query (sync) ──────────────────────────────────────────────────────────────

class TestQuery:
    def test_builder_builds_correct_payload(self, anto: Antonlytics, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            method="POST", url=f"{BASE}/api/v1/query/proj_1/execute/",
            json={"success": True, "rows": [{"name": "Alice"}],
                  "total": 1, "columns": ["name"], "execution_ms": 5},
        )
        result = (
            anto.query.build("proj_1")
            .select("Customer", alias="c1")
                .properties("name", "email", "country")
                .eq("country", "USA")
                .gte("age", 18)
                .relates_to("PURCHASED", "p1")
            .done()
            .select("Product", alias="p1")
                .properties("title", "price")
                .lte("price", 1000)
            .done()
            .order_by("age", direction="desc")
            .limit(25)
            .name("test query")
            .run()
        )
        assert result.total == 1
        assert result.rows[0]["name"] == "Alice"

        req = httpx_mock.get_request()
        body = __import__("json").loads(req.content)
        assert len(body["entities"]) == 2

        c1 = body["entities"][0]
        assert c1["alias"] == "c1"
        assert c1["type"] == "Customer"
        assert c1["properties"] == ["name", "email", "country"]
        assert c1["filters"] == [
            {"property": "country", "operator": "eq", "value": "USA"},
            {"property": "age", "operator": "gte", "value": 18},
        ]
        assert c1["relationship"] == {"type": "PURCHASED", "target": "p1"}
        assert body["orderBy"] == {"property": "age", "direction": "desc"}
        assert body["limit"] == 25

    def test_all_filter_operators(self, anto: Antonlytics):
        qb = anto.query.build("p")
        eb = qb.select("X", alias="x1")
        eb.eq("a", 1).neq("b", 2).contains("c", "x").starts_with("d", "y") \
          .ends_with("e", "z").gt("f", 3).gte("g", 4).lt("h", 5).lte("i", 6)
        payload = qb.to_dict()
        ops = [f["operator"] for f in payload["entities"][0]["filters"]]
        assert ops == ["eq", "neq", "contains", "starts_with", "ends_with", "gt", "gte", "lt", "lte"]

    def test_auto_alias(self, anto: Antonlytics):
        payload = anto.query.build("p").select("Customer").done().to_dict()
        assert payload["entities"][0]["alias"] == "customer1"

    def test_limit_capped_at_1000(self, anto: Antonlytics):
        payload = anto.query.build("p").select("X").done().limit(9999).to_dict()
        assert payload["limit"] == 1000

# ── Projects (sync) ───────────────────────────────────────────────────────────

class TestProjects:
    def test_list_unwraps_results(self, anto: Antonlytics, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url=f"{BASE}/api/v1/graph/projects/",
            json={"results": [{"id": "p1", "name": "My Graph", "description": "",
                                "team": "t1", "created_by": None, "created_at": ""}]},
        )
        projects = anto.projects.list()
        assert len(projects) == 1
        assert projects[0].name == "My Graph"

    def test_stats(self, anto: Antonlytics, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url=f"{BASE}/api/v1/graph/projects/p1/stats/",
            json={"success": True, "stats": {
                "total_entities": 500, "total_relationships": 800,
                "entity_types": 4, "relationship_types": 3,
            }},
        )
        stats = anto.projects.stats("p1")
        assert stats.total_entities == 500
        assert stats.relationship_types == 3

# ── Async client ──────────────────────────────────────────────────────────────

class TestAsync:
    @pytest.mark.asyncio
    async def test_async_ingest(self, async_anto: AsyncAntonlytics, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            method="POST", url=f"{BASE}/api/v1/ingest/",
            json={"success": True, "event_id": "e1", "async": False,
                  "results": {"created_entities": 1, "updated_entities": 0,
                              "created_relationships": 0, "errors": []}},
            status_code=201,
        )
        result = await async_anto.ingest.send("proj_1", triplet())
        assert result.success is True

    @pytest.mark.asyncio
    async def test_async_query(self, async_anto: AsyncAntonlytics, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            method="POST", url=f"{BASE}/api/v1/query/p1/execute/",
            json={"success": True, "rows": [{"x": 1}],
                  "total": 1, "columns": ["x"], "execution_ms": 3},
        )
        result = await async_anto.query.execute("p1", {
            "entities": [{"alias": "e1", "type": "X"}], "limit": 10,
        })
        assert result.total == 1

    @pytest.mark.asyncio
    async def test_async_context_manager(self, httpx_mock: HTTPXMock):
        async with AsyncAntonlytics(
            api_key="anto_live_testkey",
            base_url=BASE,
            max_retries=0,
        ) as anto:
            assert anto is not None

# ── HTTP headers ──────────────────────────────────────────────────────────────

class TestHeaders:
    def test_sends_api_key_header(self, anto: Antonlytics, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url=f"{BASE}/api/v1/graph/projects/",
            json={"results": []},
        )
        anto.projects.list()
        req = httpx_mock.get_request()
        assert req.headers["x-api-key"] == "anto_live_testkey123"
        assert req.headers["x-sdk-language"] == "python"
        assert "x-sdk-version" in req.headers
