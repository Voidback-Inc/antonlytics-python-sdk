"""
Antonlytics SDK — Data models.

All API responses are returned as dataclasses so fields are accessible
with dot notation and type checkers can verify your code.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


# ── Triplets ──────────────────────────────────────────────────────────────────

@dataclass
class EntityRef:
    """A node reference in a triplet."""
    type: str
    id: Optional[str] = None
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"type": self.type}
        if self.id is not None:
            d["id"] = self.id
        if self.properties:
            d["properties"] = self.properties
        return d


@dataclass
class Triplet:
    """
    A subject–predicate–object triple that describes a relationship
    between two entities in the knowledge graph.

    Example::

        Triplet(
            subject=EntityRef("Customer", id="cust_1", properties={"name": "Alice"}),
            predicate="PURCHASED",
            object=EntityRef("Product", id="prod_5", properties={"title": "Laptop"}),
            relationship_properties={"quantity": 2},
        )
    """
    subject: EntityRef
    predicate: str
    object: EntityRef
    relationship_properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "subject": self.subject.to_dict(),
            "predicate": self.predicate,
            "object": self.object.to_dict(),
        }
        if self.relationship_properties:
            d["relationship_properties"] = self.relationship_properties
        return d


# ── Ingestion ─────────────────────────────────────────────────────────────────

@dataclass
class IngestResults:
    created_entities: int = 0
    updated_entities: int = 0
    created_relationships: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "IngestResults":
        return cls(
            created_entities=d.get("created_entities", 0),
            updated_entities=d.get("updated_entities", 0),
            created_relationships=d.get("created_relationships", 0),
            errors=d.get("errors", []),
        )


@dataclass
class IngestResponse:
    success: bool
    event_id: str
    is_async: bool
    message: Optional[str] = None
    results: Optional[IngestResults] = None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "IngestResponse":
        results = None
        if d.get("results"):
            results = IngestResults.from_dict(d["results"])
        return cls(
            success=d.get("success", False),
            event_id=d.get("event_id", ""),
            is_async=d.get("async", False),
            message=d.get("message"),
            results=results,
        )


@dataclass
class IngestionEvent:
    id: str
    status: str  # "pending" | "processing" | "done" | "failed"
    triplets_count: int
    error_message: Optional[str] = None
    processed_at: Optional[str] = None
    created_at: str = ""

    @property
    def is_done(self) -> bool:
        return self.status == "done"

    @property
    def is_failed(self) -> bool:
        return self.status == "failed"

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "IngestionEvent":
        return cls(
            id=d.get("id", ""),
            status=d.get("status", ""),
            triplets_count=d.get("triplets_count", 0),
            error_message=d.get("error_message"),
            processed_at=d.get("processed_at"),
            created_at=d.get("created_at", ""),
        )


# ── Ontology ──────────────────────────────────────────────────────────────────

@dataclass
class PropertyDef:
    name: str
    type: str

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "PropertyDef":
        return cls(name=d.get("name", ""), type=d.get("type", "str"))


@dataclass
class RelationshipDef:
    name: str
    target: str

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "RelationshipDef":
        return cls(name=d.get("name", ""), target=d.get("target", ""))


@dataclass
class EntityTypeDef:
    id: Optional[str]
    properties: list[PropertyDef]
    relationships: list[RelationshipDef]

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "EntityTypeDef":
        return cls(
            id=d.get("id"),
            properties=[PropertyDef.from_dict(p) for p in d.get("properties", [])],
            relationships=[RelationshipDef.from_dict(r) for r in d.get("relationships", [])],
        )


# OntologyTree is a plain dict for easy key lookup: tree["Customer"].properties
OntologyTree = dict[str, EntityTypeDef]


# ── Query ─────────────────────────────────────────────────────────────────────

@dataclass
class QueryFilter:
    property: str
    operator: str  # "eq"|"neq"|"contains"|"starts_with"|"ends_with"|"gt"|"gte"|"lt"|"lte"
    value: Any

    def to_dict(self) -> dict[str, Any]:
        return {"property": self.property, "operator": self.operator, "value": self.value}


@dataclass
class RelationshipSpec:
    type: str
    target: str  # alias of the target entity node

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "target": self.target}


@dataclass
class EntitySpec:
    alias: str
    type: str
    properties: list[str] = field(default_factory=list)
    filters: list[QueryFilter] = field(default_factory=list)
    relationship: Optional[RelationshipSpec] = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"alias": self.alias, "type": self.type}
        if self.properties:
            d["properties"] = self.properties
        if self.filters:
            d["filters"] = [f.to_dict() for f in self.filters]
        if self.relationship:
            d["relationship"] = self.relationship.to_dict()
        return d


@dataclass
class OrderBy:
    property: str
    direction: str = "asc"  # "asc" | "desc"

    def to_dict(self) -> dict[str, Any]:
        return {"property": self.property, "direction": self.direction}


@dataclass
class QueryResult:
    success: bool
    rows: list[dict[str, Any]]
    total: int
    columns: list[str]
    execution_ms: int

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "QueryResult":
        return cls(
            success=d.get("success", False),
            rows=d.get("rows", []),
            total=d.get("total", 0),
            columns=d.get("columns", []),
            execution_ms=d.get("execution_ms", 0),
        )

    def __iter__(self):
        """Iterate over rows directly: `for row in result`"""
        return iter(self.rows)

    def __len__(self) -> int:
        return self.total


# ── Dashboard ─────────────────────────────────────────────────────────────────

@dataclass
class DashboardSummary:
    events_tracked: int = 0
    active_entities: int = 0
    total_relationships: int = 0
    query_usage: int = 0

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "DashboardSummary":
        return cls(
            events_tracked=d.get("events_tracked", 0),
            active_entities=d.get("active_entities", 0),
            total_relationships=d.get("total_relationships", 0),
            query_usage=d.get("query_usage", 0),
        )


@dataclass
class ChartDataset:
    type: str
    label: str
    data: list[dict[str, Any]]

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ChartDataset":
        return cls(type=d.get("type", ""), label=d.get("label", ""), data=d.get("data", []))


@dataclass
class DashboardMetrics:
    project_id: str
    project_name: str
    summary: DashboardSummary
    event_volume: ChartDataset
    entity_distribution: ChartDataset
    relationship_growth: ChartDataset
    top_ontology_queries: list[dict[str, Any]]
    recent_events: list[IngestionEvent]

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "DashboardMetrics":
        charts = d.get("charts", {})
        return cls(
            project_id=d.get("project_id", ""),
            project_name=d.get("project_name", ""),
            summary=DashboardSummary.from_dict(d.get("summary", {})),
            event_volume=ChartDataset.from_dict(charts.get("event_volume", {})),
            entity_distribution=ChartDataset.from_dict(charts.get("entity_distribution", {})),
            relationship_growth=ChartDataset.from_dict(charts.get("relationship_growth", {})),
            top_ontology_queries=d.get("top_ontology_queries", []),
            recent_events=[IngestionEvent.from_dict(e) for e in d.get("recent_events", [])],
        )


# ── Projects ──────────────────────────────────────────────────────────────────

@dataclass
class Project:
    id: str
    name: str
    description: str
    team: str
    created_by: Optional[str]
    created_at: str

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Project":
        return cls(
            id=d.get("id", ""),
            name=d.get("name", ""),
            description=d.get("description", ""),
            team=d.get("team", ""),
            created_by=d.get("created_by"),
            created_at=d.get("created_at", ""),
        )


@dataclass
class GraphStats:
    total_entities: int = 0
    total_relationships: int = 0
    entity_types: int = 0
    relationship_types: int = 0

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "GraphStats":
        return cls(
            total_entities=d.get("total_entities", 0),
            total_relationships=d.get("total_relationships", 0),
            entity_types=d.get("entity_types", 0),
            relationship_types=d.get("relationship_types", 0),
        )
