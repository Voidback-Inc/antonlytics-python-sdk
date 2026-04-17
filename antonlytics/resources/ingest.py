"""Antonlytics — Ingestion resource (sync + async)."""
from __future__ import annotations

import time
from typing import Any, Callable, Optional, Union

from ..exceptions import IngestionFailedError, PollTimeoutError
from ..models import IngestResponse, IngestionEvent, Triplet


def _build_payload(project_id: str, triplets: Union[Triplet, list[Triplet]]) -> dict[str, Any]:
    items = [triplets] if isinstance(triplets, Triplet) else triplets
    if not items:
        raise ValueError("At least one triplet is required.")
    return {
        "project_id": project_id,
        "triplets": [t.to_dict() for t in items],
    }


# ── Synchronous ───────────────────────────────────────────────────────────────

class IngestResource:
    """
    Synchronous ingestion resource.

    All data enters the knowledge graph as triplets::

        anto.ingest.track(
            project_id="proj_abc",
            triplets=Triplet(
                subject=EntityRef("Customer", id="c1", properties={"name": "Alice"}),
                predicate="PURCHASED",
                object=EntityRef("Product", id="p1", properties={"title": "Laptop"}),
            ),
        )
    """

    def __init__(self, http: Any) -> None:
        self._http = http

    def send(
        self,
        project_id: str,
        triplets: Union[Triplet, list[Triplet]],
    ) -> IngestResponse:
        """
        Ingest one or more triplets.

        Batches ≤ 100 are processed synchronously and return full results.
        Batches > 100 are queued asynchronously — use :meth:`track` to auto-poll.
        """
        data = self._http.post("/ingest/", json=_build_payload(project_id, triplets))
        return IngestResponse.from_dict(data)

    def poll(
        self,
        event_id: str,
        *,
        interval: float = 1.0,
        timeout: float = 60.0,
        on_status: Optional[Callable[[IngestionEvent], None]] = None,
    ) -> IngestionEvent:
        """
        Poll an async ingestion event until it reaches ``done`` or ``failed``.

        :param event_id: The event ID returned by :meth:`send`.
        :param interval: Seconds between polls. Default 1s.
        :param timeout:  Max seconds to wait. Default 60s.
        :param on_status: Optional callback called on each status check.
        :raises PollTimeoutError: If the event doesn't finish within *timeout*.
        :raises IngestionFailedError: If the event transitions to ``failed``.
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            data = self._http.get(f"/ingest/events/{event_id}/")
            event = IngestionEvent.from_dict(data["event"])
            if on_status:
                on_status(event)
            if event.is_done:
                return event
            if event.is_failed:
                raise IngestionFailedError(
                    event_id,
                    event.error_message or "Ingestion failed.",
                )
            time.sleep(interval)
        raise PollTimeoutError(event_id, timeout)

    def track(
        self,
        project_id: str,
        triplets: Union[Triplet, list[Triplet]],
        *,
        interval: float = 1.0,
        timeout: float = 60.0,
        on_status: Optional[Callable[[IngestionEvent], None]] = None,
    ) -> Union[IngestResponse, IngestionEvent]:
        """
        Ingest triplets and, if the job is async, automatically poll until done.

        This is the recommended method for all ingestion — it handles both
        synchronous (≤ 100 triplets) and async (> 100 triplets) transparently.

        :param project_id: Target project.
        :param triplets: A single :class:`Triplet` or a list.
        :param interval: Poll interval in seconds (for async batches).
        :param timeout:  Max poll time in seconds.
        :param on_status: Optional callback for async status updates.
        """
        result = self.send(project_id, triplets)
        if not result.is_async:
            return result
        return self.poll(result.event_id, interval=interval, timeout=timeout, on_status=on_status)

    def batch(
        self,
        project_id: str,
        triplets: list[Triplet],
        *,
        chunk_size: int = 200,
        on_chunk: Optional[Callable[[int, int, IngestResponse], None]] = None,
        interval: float = 1.0,
        timeout: float = 60.0,
    ) -> list[Union[IngestResponse, IngestionEvent]]:
        """
        Ingest a large list of triplets in chunks.

        :param chunk_size: Triplets per HTTP request. Default 200.
        :param on_chunk: Called after each chunk: ``(chunk_num, total_chunks, result)``.

        Example::

            anto.ingest.batch(
                "proj_abc",
                all_my_triplets,
                chunk_size=500,
                on_chunk=lambda i, n, r: print(f"Chunk {i}/{n}"),
            )
        """
        chunks = [triplets[i:i + chunk_size] for i in range(0, len(triplets), chunk_size)]
        results = []
        for i, chunk in enumerate(chunks, 1):
            result = self.track(project_id, chunk, interval=interval, timeout=timeout)
            results.append(result)
            if on_chunk:
                on_chunk(i, len(chunks), result)
        return results

    def status(self, event_id: str) -> IngestionEvent:
        """Fetch the current status of an ingestion event."""
        data = self._http.get(f"/ingest/events/{event_id}/")
        return IngestionEvent.from_dict(data["event"])

    def history(self, project_id: str) -> list[IngestionEvent]:
        """Return the recent ingestion event history for a project."""
        data = self._http.get(f"/ingest/history/{project_id}/")
        return [IngestionEvent.from_dict(e) for e in data.get("events", [])]


# ── Asynchronous ──────────────────────────────────────────────────────────────

class AsyncIngestResource:
    """Async version of :class:`IngestResource`. All methods are coroutines."""

    def __init__(self, http: Any) -> None:
        self._http = http

    async def send(
        self,
        project_id: str,
        triplets: Union[Triplet, list[Triplet]],
    ) -> IngestResponse:
        data = await self._http.post("/ingest/", json=_build_payload(project_id, triplets))
        return IngestResponse.from_dict(data)

    async def poll(
        self,
        event_id: str,
        *,
        interval: float = 1.0,
        timeout: float = 60.0,
        on_status: Optional[Callable[[IngestionEvent], None]] = None,
    ) -> IngestionEvent:
        import asyncio
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            data = await self._http.get(f"/ingest/events/{event_id}/")
            event = IngestionEvent.from_dict(data["event"])
            if on_status:
                on_status(event)
            if event.is_done:
                return event
            if event.is_failed:
                raise IngestionFailedError(event_id, event.error_message or "Ingestion failed.")
            await asyncio.sleep(interval)
        raise PollTimeoutError(event_id, timeout)

    async def track(
        self,
        project_id: str,
        triplets: Union[Triplet, list[Triplet]],
        *,
        interval: float = 1.0,
        timeout: float = 60.0,
        on_status: Optional[Callable[[IngestionEvent], None]] = None,
    ) -> Union[IngestResponse, IngestionEvent]:
        result = await self.send(project_id, triplets)
        if not result.is_async:
            return result
        return await self.poll(result.event_id, interval=interval, timeout=timeout, on_status=on_status)

    async def batch(
        self,
        project_id: str,
        triplets: list[Triplet],
        *,
        chunk_size: int = 200,
        on_chunk: Optional[Callable[[int, int, IngestResponse], None]] = None,
        interval: float = 1.0,
        timeout: float = 60.0,
    ) -> list[Union[IngestResponse, IngestionEvent]]:
        chunks = [triplets[i:i + chunk_size] for i in range(0, len(triplets), chunk_size)]
        results = []
        for i, chunk in enumerate(chunks, 1):
            result = await self.track(project_id, chunk, interval=interval, timeout=timeout)
            results.append(result)
            if on_chunk:
                on_chunk(i, len(chunks), result)
        return results

    async def status(self, event_id: str) -> IngestionEvent:
        data = await self._http.get(f"/ingest/events/{event_id}/")
        return IngestionEvent.from_dict(data["event"])

    async def history(self, project_id: str) -> list[IngestionEvent]:
        data = await self._http.get(f"/ingest/history/{project_id}/")
        return [IngestionEvent.from_dict(e) for e in data.get("events", [])]
