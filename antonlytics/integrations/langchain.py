"""
LangChain memory adapter.

Usage:
    from antonlytics import Agent
    from antonlytics.integrations.langchain import AntonlyticsMemory

    agent  = Agent(api_key="...", project_id="...")
    memory = AntonlyticsMemory(agent=agent)

    # Drop into any LangChain chain that accepts a memory.

Install the LangChain extras first:
    pip install antonlytics[langchain]
"""
from typing import Any, Dict, List, Optional

try:
    from langchain_core.memory import BaseMemory
    from pydantic import Field
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "AntonlyticsMemory requires langchain-core. Install with: "
        "pip install antonlytics[langchain]"
    ) from exc

from ..agent import Agent


def _format_graph(graph: Dict[str, Any]) -> str:
    entities = graph.get("entities") or []
    rels = graph.get("relationships") or []
    if not entities and not rels:
        return ""

    lines: List[str] = []
    if entities:
        lines.append("Known facts:")
        for e in entities[:50]:
            props = e.get("properties") or {}
            name = props.get("name") or e.get("name") or e.get("external_id") or ""
            extras = ", ".join(f"{k}: {v}" for k, v in props.items() if k != "name")
            lines.append(f"- [{e.get('type', '?')}] {name}" + (f" — {extras}" if extras else ""))

    if rels:
        # Build id → name map from entities for readable relationships.
        id_to_name = {e.get("id"): (e.get("properties") or {}).get("name", "") for e in entities}
        lines.append("Relationships:")
        for r in rels[:50]:
            src = id_to_name.get(r.get("source_id"), r.get("source_id", "?"))
            tgt = id_to_name.get(r.get("target_id"), r.get("target_id", "?"))
            lines.append(f"- {src} --[{r.get('type', '?')}]--> {tgt}")

    return "\n".join(lines)


class AntonlyticsMemory(BaseMemory):
    """LangChain BaseMemory backed by an Antonlytics project.

    `load_memory_variables` fetches a question-scoped slice of the knowledge
    graph and formats it into a string suitable for a prompt.
    `save_context` ingests the new turn so the next call sees it.
    """

    agent: Agent
    memory_key: str = Field(default="history")
    input_key: Optional[str] = Field(default="input")
    output_key: Optional[str] = Field(default=None)
    return_messages: bool = Field(default=False)

    class Config:
        arbitrary_types_allowed = True

    @property
    def memory_variables(self) -> List[str]:
        return [self.memory_key]

    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        query = ""
        if self.input_key and self.input_key in inputs:
            query = str(inputs[self.input_key])
        elif inputs:
            # Fall back to the first stringy value.
            for v in inputs.values():
                if isinstance(v, str):
                    query = v
                    break
        try:
            graph = self.agent.get_memory(query=query or None)
        except Exception:
            graph = {}
        return {self.memory_key: _format_graph(graph)}

    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> None:
        user_msg = ""
        if self.input_key and self.input_key in inputs:
            user_msg = str(inputs[self.input_key])
        ai_msg = ""
        if self.output_key and self.output_key in outputs:
            ai_msg = str(outputs[self.output_key])
        elif outputs:
            for v in outputs.values():
                if isinstance(v, str):
                    ai_msg = v
                    break

        turn = ""
        if user_msg:
            turn += f"User: {user_msg}\n"
        if ai_msg:
            turn += f"Assistant: {ai_msg}"
        turn = turn.strip()
        if not turn:
            return

        try:
            self.agent.ingest(turn)
        except Exception:
            # Never break the chain just because ingest hiccuped.
            pass

    def clear(self) -> None:
        # Project-level wipe is not exposed by the API yet — intentional no-op.
        return None
