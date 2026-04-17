"""
Antonlytics Python SDK
======================

Official Python client for the Antonlytics Knowledge Graph API.

Quick start::

    from antonlytics import Antonlytics, Triplet, EntityRef

    anto = Antonlytics(api_key="anto_live_xxx")

    # Ingest a relationship
    anto.ingest.track(
        project_id="proj_abc",
        triplets=Triplet(
            subject=EntityRef("Customer", id="c1", properties={"name": "Alice"}),
            predicate="PURCHASED",
            object=EntityRef("Product", id="p1", properties={"title": "Laptop Pro"}),
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
        print(row)
"""

from .client import Antonlytics, AsyncAntonlytics
from .exceptions import (
    AntoError,
    AuthenticationError,
    IngestionFailedError,
    InvalidConfigError,
    NetworkError,
    NotFoundError,
    PermissionError,
    PlanLimitError,
    PollTimeoutError,
    RateLimitError,
    ServerError,
    TimeoutError,
    ValidationError,
)
from .models import (
    ChartDataset,
    DashboardMetrics,
    DashboardSummary,
    EntityRef,
    EntitySpec,
    EntityTypeDef,
    GraphStats,
    IngestResponse,
    IngestResults,
    IngestionEvent,
    OntologyTree,
    OrderBy,
    Project,
    PropertyDef,
    QueryFilter,
    QueryResult,
    RelationshipDef,
    RelationshipSpec,
    Triplet,
)

__version__ = "1.0.0"
__author__  = "Antonlytics"
__email__   = "sdk@antonlytics.com"

__all__ = [
    # Clients
    "Antonlytics",
    "AsyncAntonlytics",
    # Models
    "Triplet",
    "EntityRef",
    "EntitySpec",
    "QueryFilter",
    "OrderBy",
    "RelationshipSpec",
    "QueryResult",
    "IngestResponse",
    "IngestResults",
    "IngestionEvent",
    "Project",
    "GraphStats",
    "OntologyTree",
    "EntityTypeDef",
    "PropertyDef",
    "RelationshipDef",
    "DashboardMetrics",
    "DashboardSummary",
    "ChartDataset",
    # Exceptions
    "AntoError",
    "AuthenticationError",
    "PermissionError",
    "NotFoundError",
    "PlanLimitError",
    "ValidationError",
    "RateLimitError",
    "ServerError",
    "NetworkError",
    "TimeoutError",
    "IngestionFailedError",
    "PollTimeoutError",
    "InvalidConfigError",
]
