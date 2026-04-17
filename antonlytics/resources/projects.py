"""Antonlytics — Projects and Dashboard resources (sync + async)."""
from __future__ import annotations

from typing import Any, Optional

from ..models import DashboardMetrics, GraphStats, OntologyTree, EntityTypeDef, Project


# ── Projects — Sync ───────────────────────────────────────────────────────────

class ProjectsResource:
    def __init__(self, http: Any) -> None:
        self._http = http

    def list(self) -> list[Project]:
        """List all projects accessible to this API key."""
        data = self._http.get("/graph/projects/")
        items = data if isinstance(data, list) else data.get("results", [])
        return [Project.from_dict(p) for p in items]

    def get(self, project_id: str) -> Project:
        """Fetch a single project by ID."""
        data = self._http.get(f"/graph/projects/{project_id}/")
        return Project.from_dict(data)

    def create(
        self,
        name: str,
        team_id: str,
        description: str = "",
    ) -> Project:
        """
        Create a new project.

        Example::

            project = anto.projects.create(
                name="E-Commerce Graph",
                team_id="team-uuid",
            )
            print(project.id)
        """
        data = self._http.post("/graph/projects/", json={
            "name": name,
            "description": description,
            "team_id": team_id,
        })
        return Project.from_dict(data)

    def stats(self, project_id: str) -> GraphStats:
        """Get entity and relationship counts for a project."""
        data = self._http.get(f"/graph/projects/{project_id}/stats/")
        return GraphStats.from_dict(data.get("stats", data))

    def ontology(self, project_id: str) -> OntologyTree:
        """Fetch the full ontology schema for a project."""
        data = self._http.get(f"/graph/projects/{project_id}/ontology/")
        return {
            name: EntityTypeDef.from_dict(d)
            for name, d in data.get("ontology", {}).items()
        }


# ── Projects — Async ──────────────────────────────────────────────────────────

class AsyncProjectsResource:
    def __init__(self, http: Any) -> None:
        self._http = http

    async def list(self) -> list[Project]:
        data = await self._http.get("/graph/projects/")
        items = data if isinstance(data, list) else data.get("results", [])
        return [Project.from_dict(p) for p in items]

    async def get(self, project_id: str) -> Project:
        data = await self._http.get(f"/graph/projects/{project_id}/")
        return Project.from_dict(data)

    async def create(self, name: str, team_id: str, description: str = "") -> Project:
        data = await self._http.post("/graph/projects/", json={
            "name": name, "description": description, "team_id": team_id,
        })
        return Project.from_dict(data)

    async def stats(self, project_id: str) -> GraphStats:
        data = await self._http.get(f"/graph/projects/{project_id}/stats/")
        return GraphStats.from_dict(data.get("stats", data))

    async def ontology(self, project_id: str) -> OntologyTree:
        data = await self._http.get(f"/graph/projects/{project_id}/ontology/")
        return {
            name: EntityTypeDef.from_dict(d)
            for name, d in data.get("ontology", {}).items()
        }


# ── Dashboard — Sync ──────────────────────────────────────────────────────────

class DashboardResource:
    def __init__(self, http: Any) -> None:
        self._http = http

    def metrics(self, project_id: str) -> DashboardMetrics:
        """
        Fetch all dashboard metrics in one call.

        Returns summary counts plus chart-ready datasets::

            m = anto.dashboard.metrics("proj_abc")

            print(m.summary.active_entities)
            print(m.summary.total_relationships)

            # Scatter chart: event volume over time
            for point in m.event_volume.data:
                print(point["date"], point["count"])

            # Pie chart: entity type distribution
            for point in m.entity_distribution.data:
                print(point["name"], point["value"])

            # Histogram: relationship growth
            for point in m.relationship_growth.data:
                print(point["date"], point["cumulative"])

            # Top queries
            for q in m.top_ontology_queries:
                print(q["name"], q["count"])

            # Recent ingestion events
            for e in m.recent_events:
                print(e.status, e.triplets_count)
        """
        data = self._http.get(f"/dashboard/{project_id}/metrics/")
        return DashboardMetrics.from_dict(data)


# ── Dashboard — Async ─────────────────────────────────────────────────────────

class AsyncDashboardResource:
    def __init__(self, http: Any) -> None:
        self._http = http

    async def metrics(self, project_id: str) -> DashboardMetrics:
        data = await self._http.get(f"/dashboard/{project_id}/metrics/")
        return DashboardMetrics.from_dict(data)
