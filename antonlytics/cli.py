"""
anto — Antonlytics CLI

Usage:
    ANTO_API_KEY=anto_live_xxx anto <command> [args]

Commands:
    projects                        List all projects
    stats       <project-id>        Graph statistics
    ontology    <project-id>        Print ontology schema
    ingest      <project-id> <file> Ingest triplets from JSON file
    query       <project-id> <file> Execute a JSON query file
    dashboard   <project-id>        Print dashboard summary
    poll        <event-id>          Poll an async ingestion event
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from .client import Antonlytics
from .exceptions import AntoError
from .models import EntityRef, Triplet


# ── ANSI colours (auto-disabled when not a TTY) ───────────────────────────────

_IS_TTY = sys.stdout.isatty()


def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _IS_TTY else text


def bold(t: str)  -> str: return _c("1",  t)
def dim(t: str)   -> str: return _c("2",  t)
def amber(t: str) -> str: return _c("33", t)
def green(t: str) -> str: return _c("32", t)
def red(t: str)   -> str: return _c("31", t)
def cyan(t: str)  -> str: return _c("36", t)


# ── Helpers ───────────────────────────────────────────────────────────────────

def out(msg: str = "") -> None:
    print(msg)

def err(msg: str = "") -> None:
    print(msg, file=sys.stderr)

def die(msg: str) -> None:
    print(f"\n  {red('✗')} {msg}\n", file=sys.stderr)
    sys.exit(1)

def hdr(title: str) -> None:
    out()
    out(f"  {bold(title)}")
    out(f"  {'═' * max(len(title), 36)}")

def row(label: str, value: Any) -> None:
    out(f"  {dim(label.ljust(22))}  {bold(str(value))}")

def need(args: list[str], idx: int, name: str) -> str:
    if idx >= len(args):
        die(f"Missing argument: <{name}>")
    return args[idx]


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_projects(anto: Antonlytics) -> None:
    projects = anto.projects.list()
    hdr("PROJECTS")
    if not projects:
        out("  No projects found.")
        return
    for p in projects:
        out(f"  {amber(p.id[:8])}…  {bold(p.name)}  {dim(p.description or '')}")


def cmd_stats(anto: Antonlytics, project_id: str) -> None:
    s = anto.projects.stats(project_id)
    hdr("GRAPH STATS")
    row("Entity types",         s.entity_types)
    row("Relationship types",   s.relationship_types)
    row("Total entities",       f"{s.total_entities:,}")
    row("Total relationships",  f"{s.total_relationships:,}")


def cmd_ontology(anto: Antonlytics, project_id: str) -> None:
    tree = anto.query.ontology(project_id)
    hdr("ONTOLOGY")
    for type_name, defn in tree.items():
        out(f"\n  {bold(amber(type_name))}")
        out(f"  {'─' * 36}")
        if defn.properties:
            out(f"  {dim('Properties')}")
            for p in defn.properties:
                out(f"    {p.name.ljust(22)} {dim(p.type)}")
        if defn.relationships:
            out(f"  {dim('Relationships')}")
            for r in defn.relationships:
                out(f"    {green(f'─[{r.name}]→')}  {r.target}")


def cmd_ingest(anto: Antonlytics, project_id: str, file_path: str) -> None:
    raw = Path(file_path).read_text()
    data = json.loads(raw)
    raw_triplets = data if isinstance(data, list) else [data]

    hdr("INGEST")
    row("File",      file_path)
    row("Triplets",  len(raw_triplets))
    out()

    triplets = [
        Triplet(
            subject=EntityRef(**t["subject"]),
            predicate=t["predicate"],
            object=EntityRef(**t["object"]),
            relationship_properties=t.get("relationship_properties", {}),
        )
        for t in raw_triplets
    ]

    def on_status(event: Any) -> None:
        err(f"  polling… {event.status}")

    result = anto.ingest.track(project_id, triplets, on_status=on_status)

    if hasattr(result, "results") and result.results:  # type: ignore[union-attr]
        r = result.results  # type: ignore[union-attr]
        row("Entities created",      r.created_entities)
        row("Entities updated",      r.updated_entities)
        row("Relationships created", r.created_relationships)
        if r.errors:
            out(f"\n  {red(f'Errors: {len(r.errors)}')}")
            for e in r.errors[:5]:
                out(f"    [{e['index']}] {e['error']}")
    else:
        row("Event ID", getattr(result, "id", getattr(result, "event_id", "queued")))
        row("Status",   getattr(result, "status", "done"))


def cmd_query(anto: Antonlytics, project_id: str, file_path: str) -> None:
    payload = json.loads(Path(file_path).read_text())
    hdr("QUERY")
    result = anto.query.execute(project_id, payload)
    row("Total",     result.total)
    row("Execution", f"{result.execution_ms}ms")
    out()

    if not result.rows:
        out("  No results.")
        return

    cols = result.columns or [k for k in result.rows[0] if not k.startswith("_")]
    widths = [
        min(28, max(len(c), max((len(str(r.get(c, ""))) for r in result.rows[:30]), default=0)))
        for c in cols
    ]
    out("  " + bold("  ".join(c.ljust(w) for c, w in zip(cols, widths))))
    out("  " + "  ".join("─" * w for w in widths))
    for r in result.rows[:50]:
        out("  " + "  ".join(str(r.get(c, "")).ljust(w)[:w] for c, w in zip(cols, widths)))
    if result.total > 50:
        out(f"\n  {dim(f'…and {result.total - 50} more rows')}")


def cmd_dashboard(anto: Antonlytics, project_id: str) -> None:
    m = anto.dashboard.metrics(project_id)
    hdr(f"DASHBOARD · {m.project_name}")
    out(f"\n  {dim('SUMMARY')}")
    row("Events tracked",      f"{m.summary.events_tracked:,}")
    row("Active entities",     f"{m.summary.active_entities:,}")
    row("Relationships",       f"{m.summary.total_relationships:,}")
    row("Query usage",         f"{m.summary.query_usage:,}")

    if m.top_ontology_queries:
        out(f"\n  {dim('TOP QUERIES')}")
        for q in m.top_ontology_queries[:8]:
            out(f"    {str(q['count']).rjust(6)}  {q['name']}")

    if m.recent_events:
        out(f"\n  {dim('RECENT EVENTS')}")
        for e in m.recent_events:
            col = green if e.is_done else (red if e.is_failed else amber)
            out(f"    {col(e.status.ljust(12))}  {e.triplets_count} triplets  {dim(e.created_at)}")


def cmd_poll(anto: Antonlytics, event_id: str) -> None:
    hdr(f"POLLING · {event_id}")

    def on_status(event: Any) -> None:
        out(f"  {dim(time.strftime('%H:%M:%S'))}  {amber(event.status)}")

    event = anto.ingest.poll(event_id, timeout=120.0, on_status=on_status)
    out()
    row("Status",      event.status)
    row("Triplets",    event.triplets_count)
    row("Finished at", event.processed_at or "—")


def cmd_help() -> None:
    out(f"""
  {bold('anto')} — Antonlytics CLI  {dim('v1.0.0')}

  {dim('Environment:')}
    ANTO_API_KEY    Your API key  {dim('(required)')}
    ANTO_BASE_URL   API base URL  {dim('(default: https://api.antonlytics.com)')}
    ANTO_DEBUG=1    Log raw HTTP requests

  {dim('Commands:')}
    {amber('projects')}                          List all projects
    {amber('stats')}      {dim('<project-id>')}           Graph statistics
    {amber('ontology')}   {dim('<project-id>')}           Print ontology schema
    {amber('ingest')}     {dim('<project-id> <file>')}    Ingest triplets JSON file
    {amber('query')}      {dim('<project-id> <file>')}    Execute JSON query file
    {amber('dashboard')}  {dim('<project-id>')}           Print dashboard summary
    {amber('poll')}       {dim('<event-id>')}             Poll async ingestion event

  {dim('Examples:')}
    ANTO_API_KEY=anto_live_xxx anto projects
    ANTO_API_KEY=anto_live_xxx anto ingest proj_abc ./triplets.json
    ANTO_API_KEY=anto_live_xxx anto dashboard proj_abc
""")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    api_key = os.environ.get("ANTO_API_KEY", "")
    if not api_key:
        die("Set ANTO_API_KEY environment variable.\n  export ANTO_API_KEY=anto_live_xxx")

    base_url = os.environ.get("ANTO_BASE_URL", "https://api.antonlytics.com")
    debug    = os.environ.get("ANTO_DEBUG") == "1"

    args = sys.argv[1:]
    cmd  = args[0] if args else ""

    if cmd in ("--help", "-h", "help", ""):
        cmd_help()
        return

    try:
        anto = Antonlytics(api_key=api_key, base_url=base_url, debug=debug)

        if   cmd == "projects":   cmd_projects(anto)
        elif cmd == "stats":      cmd_stats(anto, need(args, 1, "project-id"))
        elif cmd == "ontology":   cmd_ontology(anto, need(args, 1, "project-id"))
        elif cmd == "ingest":     cmd_ingest(anto, need(args, 1, "project-id"), need(args, 2, "file"))
        elif cmd == "query":      cmd_query(anto, need(args, 1, "project-id"), need(args, 2, "file"))
        elif cmd == "dashboard":  cmd_dashboard(anto, need(args, 1, "project-id"))
        elif cmd == "poll":       cmd_poll(anto, need(args, 1, "event-id"))
        else:
            die(f"Unknown command: '{cmd}'. Run 'anto --help' for usage.")

        anto.close()

    except AntoError as e:
        die(f"[{e.code}] {e.message}" + (f" (HTTP {e.status})" if e.status else ""))
    except KeyboardInterrupt:
        out()
        sys.exit(0)


if __name__ == "__main__":
    main()
