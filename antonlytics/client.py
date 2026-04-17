"""
Antonlytics Python SDK — Client classes.

Use :class:`Antonlytics` for synchronous code and :class:`AsyncAntonlytics`
for async/await code (FastAPI, asyncio, etc.).
"""
from __future__ import annotations

from typing import Optional

from ._http import HttpClient, AsyncHttpClient
from .exceptions import InvalidConfigError
from .resources import (
    IngestResource, AsyncIngestResource,
    QueryResource, AsyncQueryResource,
    ProjectsResource, AsyncProjectsResource,
    DashboardResource, AsyncDashboardResource,
)

DEFAULT_BASE_URL = "https://api.antonlytics.com"
SDK_VERSION = "1.0.0"


def _validate_api_key(api_key: str) -> None:
    if not api_key or not isinstance(api_key, str) or not api_key.strip():
        raise InvalidConfigError(
            "apiKey is required. Get yours at app.antonlytics.com → API Keys."
        )
    if not api_key.startswith("anto_"):
        raise InvalidConfigError(
            f'Invalid API key format. Antonlytics keys start with "anto_live_". '
            f'Got: "{api_key[:12]}..."'
        )


class Antonlytics:
    """
    Synchronous Antonlytics client.

    Create one instance and reuse it for the lifetime of your application.

    Example::

        from antonlytics import Antonlytics, Triplet, EntityRef

        anto = Antonlytics(api_key="anto_live_xxx")

        # Ingest a relationship
        anto.ingest.track(
            project_id="proj_abc",
            triplets=Triplet(
                subject=EntityRef("Customer", id="c1", properties={"name": "Alice"}),
                predicate="PURCHASED",
                object=EntityRef("Product", id="p1", properties={"title": "Laptop"}),
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

    Context manager usage::

        with Antonlytics(api_key="anto_live_xxx") as anto:
            projects = anto.projects.list()
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
        max_retries: int = 2,
        debug: bool = False,
    ) -> None:
        """
        :param api_key:     Your Antonlytics API key (``anto_live_...``).
        :param base_url:    Backend base URL. Override for self-hosted deployments.
        :param timeout:     Request timeout in seconds. Default 30.
        :param max_retries: Auto-retry on 5xx / network errors. Default 2.
        :param debug:       Print HTTP requests/responses to stdout. Default False.
        """
        _validate_api_key(api_key)

        self._http = HttpClient(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
            debug=debug,
        )

        #: Ingest triplets into the knowledge graph
        self.ingest = IngestResource(self._http)
        #: Build and execute ontology queries
        self.query = QueryResource(self._http)
        #: Project management and graph statistics
        self.projects = ProjectsResource(self._http)
        #: Dashboard metrics and chart data
        self.dashboard = DashboardResource(self._http)

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._http.close()

    def __enter__(self) -> "Antonlytics":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"Antonlytics(base_url={self._http._base!r})"


class AsyncAntonlytics:
    """
    Asynchronous Antonlytics client for use with ``async/await``.

    Identical API to :class:`Antonlytics` but all resource methods are coroutines.

    Example::

        import asyncio
        from antonlytics import AsyncAntonlytics, Triplet, EntityRef

        async def main():
            async with AsyncAntonlytics(api_key="anto_live_xxx") as anto:
                await anto.ingest.track(
                    project_id="proj_abc",
                    triplets=Triplet(
                        subject=EntityRef("Customer", id="c1"),
                        predicate="PURCHASED",
                        object=EntityRef("Product", id="p1"),
                    ),
                )

                result = await (
                    anto.query.build("proj_abc")
                    .select("Customer")
                    .eq("country", "USA")
                    .done()
                    .run()
                )
                for row in result:
                    print(row)

        asyncio.run(main())

    FastAPI example::

        from fastapi import FastAPI
        from antonlytics import AsyncAntonlytics

        app = FastAPI()
        anto = AsyncAntonlytics(api_key="anto_live_xxx")

        @app.post("/track")
        async def track_event(data: dict):
            return await anto.ingest.track(
                project_id=data["project_id"],
                triplets=data["triplets"],
            )
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
        max_retries: int = 2,
        debug: bool = False,
    ) -> None:
        _validate_api_key(api_key)

        self._http = AsyncHttpClient(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
            debug=debug,
        )

        self.ingest    = AsyncIngestResource(self._http)
        self.query     = AsyncQueryResource(self._http)
        self.projects  = AsyncProjectsResource(self._http)
        self.dashboard = AsyncDashboardResource(self._http)

    async def aclose(self) -> None:
        """Close the underlying async HTTP connection pool."""
        await self._http.aclose()

    async def __aenter__(self) -> "AsyncAntonlytics":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    def __repr__(self) -> str:
        return f"AsyncAntonlytics(base_url={self._http._base!r})"
