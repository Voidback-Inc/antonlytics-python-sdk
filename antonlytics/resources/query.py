"""Antonlytics — Query resource with fluent builder (sync + async)."""
from __future__ import annotations

from typing import Any, Optional

from ..models import (
    EntitySpec, OntologyTree, EntityTypeDef,
    OrderBy, QueryFilter, QueryResult, RelationshipSpec,
)


# ── Fluent builder ────────────────────────────────────────────────────────────

class EntityBuilder:
    """
    Fluent builder for a single entity node.
    Call :meth:`done` to return to the parent :class:`QueryBuilder`.

    Example::

        (
            anto.query.build("proj_abc")
            .select("Customer", alias="c1")
                .properties("name", "email", "country")
                .eq("country", "USA")
                .gte("age", 18)
                .relates_to("PURCHASED", "p1")
            .done()
        )
    """

    def __init__(self, parent: "QueryBuilder", alias: str, entity_type: str) -> None:
        self._parent = parent
        self._spec = EntitySpec(alias=alias, type=entity_type)

    # ── Property selection ─────────────────────────────────────────────────

    def properties(self, *props: str) -> "EntityBuilder":
        """Select which properties to return. Default: all."""
        self._spec.properties = list(props)
        return self

    # ── Filters ───────────────────────────────────────────────────────────

    def where(self, property: str, operator: str, value: Any) -> "EntityBuilder":
        """Add a filter condition."""
        self._spec.filters.append(QueryFilter(property=property, operator=operator, value=value))
        return self

    def eq(self, property: str, value: Any) -> "EntityBuilder":
        """Filter: property == value"""
        return self.where(property, "eq", value)

    def neq(self, property: str, value: Any) -> "EntityBuilder":
        """Filter: property != value"""
        return self.where(property, "neq", value)

    def contains(self, property: str, value: str) -> "EntityBuilder":
        """Filter: property contains substring"""
        return self.where(property, "contains", value)

    def starts_with(self, property: str, value: str) -> "EntityBuilder":
        """Filter: property starts with prefix"""
        return self.where(property, "starts_with", value)

    def ends_with(self, property: str, value: str) -> "EntityBuilder":
        """Filter: property ends with suffix"""
        return self.where(property, "ends_with", value)

    def gt(self, property: str, value: Any) -> "EntityBuilder":
        """Filter: property > value"""
        return self.where(property, "gt", value)

    def gte(self, property: str, value: Any) -> "EntityBuilder":
        """Filter: property >= value"""
        return self.where(property, "gte", value)

    def lt(self, property: str, value: Any) -> "EntityBuilder":
        """Filter: property < value"""
        return self.where(property, "lt", value)

    def lte(self, property: str, value: Any) -> "EntityBuilder":
        """Filter: property <= value"""
        return self.where(property, "lte", value)

    # ── Relationship join ──────────────────────────────────────────────────

    def relates_to(self, relationship_type: str, target_alias: str) -> "EntityBuilder":
        """
        Join to another entity node in this query via a named relationship.

        *target_alias* must match the alias given to another ``.select()`` call.
        """
        self._spec.relationship = RelationshipSpec(type=relationship_type, target=target_alias)
        return self

    # ── Return to parent ───────────────────────────────────────────────────

    def done(self) -> "QueryBuilder":
        """Finish this entity node and return to the parent QueryBuilder."""
        return self._parent

    def _build(self) -> EntitySpec:
        return self._spec


class QueryBuilder:
    """
    Fluent query builder. Create via ``anto.query.build("project-id")``.

    Example::

        result = (
            anto.query.build("proj_abc")
            .select("Customer", alias="c1")
                .properties("name", "email", "country")
                .eq("country", "USA")
                .gte("age", 21)
                .relates_to("PURCHASED", "p1")
            .done()
            .select("Product", alias="p1")
                .properties("title", "price")
                .lte("price", 1000)
            .done()
            .order_by("age", direction="desc")
            .limit(50)
            .run()
        )
        for row in result:
            print(row["name"], row["country"])
    """

    def __init__(self, project_id: str, resource: "QueryResource") -> None:
        self._project_id = project_id
        self._resource = resource
        self._entities: list[EntityBuilder] = []
        self._order_by: Optional[OrderBy] = None
        self._limit: int = 50
        self._name: str = ""

    def select(self, entity_type: str, alias: Optional[str] = None) -> EntityBuilder:
        """Add an entity node. Returns an :class:`EntityBuilder`."""
        if alias is None:
            alias = f"{entity_type.lower()}{len(self._entities) + 1}"
        eb = EntityBuilder(self, alias, entity_type)
        self._entities.append(eb)
        return eb

    def order_by(self, property: str, direction: str = "asc") -> "QueryBuilder":
        """Sort results."""
        self._order_by = OrderBy(property=property, direction=direction)
        return self

    def limit(self, n: int) -> "QueryBuilder":
        """Maximum rows to return (max 1000)."""
        self._limit = min(n, 1000)
        return self

    def name(self, label: str) -> "QueryBuilder":
        """Human-readable name stored in query history."""
        self._name = label
        return self

    def to_dict(self) -> dict[str, Any]:
        """Serialize the query to the raw API payload."""
        payload: dict[str, Any] = {
            "entities": [e._build().to_dict() for e in self._entities],
            "limit": self._limit,
        }
        if self._order_by:
            payload["orderBy"] = self._order_by.to_dict()
        if self._name:
            payload["name"] = self._name
        return payload

    def run(self) -> QueryResult:
        """Execute the query synchronously."""
        return self._resource.execute(self._project_id, self.to_dict())


class AsyncQueryBuilder(QueryBuilder):
    """Async variant — ``.run()`` is a coroutine."""

    def __init__(self, project_id: str, resource: "AsyncQueryResource") -> None:
        super().__init__(project_id, resource)  # type: ignore[arg-type]
        self._async_resource = resource

    async def run(self) -> QueryResult:  # type: ignore[override]
        return await self._async_resource.execute(self._project_id, self.to_dict())


# ── Sync resource ─────────────────────────────────────────────────────────────

class QueryResource:
    def __init__(self, http: Any) -> None:
        self._http = http

    def build(self, project_id: str) -> QueryBuilder:
        """Create a fluent :class:`QueryBuilder` for this project."""
        return QueryBuilder(project_id, self)

    def execute(self, project_id: str, payload: dict[str, Any]) -> QueryResult:
        """Execute a raw query payload dict."""
        data = self._http.post(f"/query/{project_id}/execute/", json=payload)
        return QueryResult.from_dict(data)

    def ontology(self, project_id: str) -> OntologyTree:
        """Fetch the ontology tree — entity types, properties, and relationships."""
        data = self._http.get(f"/query/{project_id}/ontology/")
        return {
            name: EntityTypeDef.from_dict(d)
            for name, d in data.get("ontology", {}).items()
        }

    def history(self, project_id: str) -> list[QueryResult]:
        """Return recent query history for a project."""
        data = self._http.get(f"/query/{project_id}/history/")
        return [QueryResult.from_dict(r) for r in data.get("history", [])]


# ── Async resource ────────────────────────────────────────────────────────────

class AsyncQueryResource:
    def __init__(self, http: Any) -> None:
        self._http = http

    def build(self, project_id: str) -> AsyncQueryBuilder:
        return AsyncQueryBuilder(project_id, self)

    async def execute(self, project_id: str, payload: dict[str, Any]) -> QueryResult:
        data = await self._http.post(f"/query/{project_id}/execute/", json=payload)
        return QueryResult.from_dict(data)

    async def ontology(self, project_id: str) -> OntologyTree:
        data = await self._http.get(f"/query/{project_id}/ontology/")
        return {
            name: EntityTypeDef.from_dict(d)
            for name, d in data.get("ontology", {}).items()
        }

    async def history(self, project_id: str) -> list[QueryResult]:
        data = await self._http.get(f"/query/{project_id}/history/")
        return [QueryResult.from_dict(r) for r in data.get("history", [])]
