"""
Account-level client. For SaaS apps that manage many projects with one API key.

    from antonlytics import Antonlytics

    client = Antonlytics(api_key="...")

    # Create a project on the API key's team
    project = client.create_project(name="customer_42", scope="Customer 42 dataset")

    # Per-project work — same Agent surface as before
    agent = client.agent(project_id=project["id"])
    agent.ingest_triplets([...])

The Agent class is unchanged — Antonlytics is just a thin factory + project
management wrapper that reuses the same HTTPClient.
"""
from typing import Dict, Any, List, Optional

from .http_client import HTTPClient
from .agent import Agent
from .exceptions import AntonlyticsError


class Antonlytics:
    """Account-level entry point. Use this for project CRUD; use ``.agent()``
    to get a project-scoped Agent for ingestion / chat / retrieval."""

    def __init__(self, api_key: str, base_url: str = "https://api.antonlytics.com"):
        if not api_key:
            raise AntonlyticsError("API key is required")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.client = HTTPClient(api_key, self.base_url)

    # ── Project CRUD ─────────────────────────────────────────────────────

    def list_projects(self) -> List[Dict[str, Any]]:
        """Return all projects this API key has access to."""
        r = self.client.get("/api/v1/graph/projects/")
        return r.get("results", r) if isinstance(r, dict) else r

    def create_project(self, name: str, scope: Optional[str] = None,
                       description: Optional[str] = None) -> Dict[str, Any]:
        """Create a new project on the team this API key belongs to."""
        if not name or not name.strip():
            raise AntonlyticsError("Project name is required")
        payload: Dict[str, Any] = {"name": name.strip()}
        if scope:        payload["scope"] = scope
        if description:  payload["description"] = description
        return self.client.post("/api/v1/graph/projects/", payload)

    def get_project(self, project_id: str) -> Dict[str, Any]:
        return self.client.get(f"/api/v1/graph/projects/{project_id}/")

    def delete_project(self, project_id: str) -> Dict[str, Any]:
        return self.client.delete(f"/api/v1/graph/projects/{project_id}/")

    def project_stats(self, project_id: str) -> Dict[str, Any]:
        return self.client.get(f"/api/v1/graph/projects/{project_id}/stats/")

    def project_ontology(self, project_id: str) -> Dict[str, Any]:
        return self.client.get(f"/api/v1/graph/projects/{project_id}/ontology/")

    # ── Agent factory ────────────────────────────────────────────────────

    def agent(self, project_id: str) -> Agent:
        """Return an Agent scoped to ``project_id``. Reuses this client's
        API key + base URL — no extra config needed."""
        return Agent(api_key=self.api_key, project_id=project_id, base_url=self.base_url)
