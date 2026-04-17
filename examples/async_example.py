"""
examples/async_example.py — AsyncAntonlytics with FastAPI and plain asyncio.
"""
from __future__ import annotations
import asyncio
import os

from antonlytics import AsyncAntonlytics, Triplet, EntityRef, AntoError, PlanLimitError


# ── Plain asyncio ─────────────────────────────────────────────────────────────

async def main() -> None:
    async with AsyncAntonlytics(
        api_key=os.environ.get("ANTO_API_KEY", "anto_live_xxx"),
        base_url=os.environ.get("ANTO_BASE_URL", "http://localhost:8000"),
        debug=True,
    ) as anto:
        project_id = os.environ.get("ANTO_PROJECT_ID", "proj_abc")

        # Ingest
        result = await anto.ingest.track(
            project_id,
            triplets=Triplet(
                subject=EntityRef("User", id="u1", properties={"name": "Alice"}),
                predicate="SIGNED_UP",
                object=EntityRef("Plan", id="plan_free", properties={"name": "Free"}),
            ),
        )
        print("Ingested:", result)

        # Parallel queries
        ontology, metrics, projects = await asyncio.gather(
            anto.query.ontology(project_id),
            anto.dashboard.metrics(project_id),
            anto.projects.list(),
        )
        print("Entity types:", list(ontology.keys()))
        print("Active entities:", metrics.summary.active_entities)
        print("Projects:", [p.name for p in projects])

        # Fluent query
        result = await (
            anto.query.build(project_id)
            .select("User", alias="u1")
                .properties("name")
                .eq("plan", "growth")
            .done()
            .limit(10)
            .run()
        )
        print(f"Query: {result.total} rows in {result.execution_ms}ms")


# ── FastAPI integration ───────────────────────────────────────────────────────

"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any
from antonlytics import AsyncAntonlytics, Triplet, EntityRef, AntoError, PlanLimitError

app = FastAPI()

anto = AsyncAntonlytics(
    api_key=os.environ["ANTONLYTICS_API_KEY"],
    base_url=os.environ.get("ANTONLYTICS_BASE_URL", "https://api.antonlytics.com"),
)


class TrackEventRequest(BaseModel):
    project_id: str
    subject_type: str
    subject_id: str
    predicate: str
    object_type: str
    object_id: str
    subject_properties: dict[str, Any] = {}
    object_properties: dict[str, Any] = {}


@app.post("/api/track")
async def track_event(req: TrackEventRequest):
    try:
        result = await anto.ingest.track(
            req.project_id,
            triplets=Triplet(
                subject=EntityRef(req.subject_type, id=req.subject_id, properties=req.subject_properties),
                predicate=req.predicate,
                object=EntityRef(req.object_type, id=req.object_id, properties=req.object_properties),
            ),
        )
        return {"success": True, "event_id": getattr(result, "event_id", None)}
    except PlanLimitError as e:
        raise HTTPException(status_code=402, detail=str(e))
    except AntoError as e:
        raise HTTPException(status_code=e.status or 500, detail=str(e))


@app.get("/api/dashboard/{project_id}")
async def get_dashboard(project_id: str):
    metrics = await anto.dashboard.metrics(project_id)
    return {
        "summary": {
            "events_tracked": metrics.summary.events_tracked,
            "active_entities": metrics.summary.active_entities,
            "total_relationships": metrics.summary.total_relationships,
        },
        "entity_distribution": metrics.entity_distribution.data,
    }
"""

if __name__ == "__main__":
    asyncio.run(main())
