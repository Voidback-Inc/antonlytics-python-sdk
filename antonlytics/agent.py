"""
Agent class for interacting with Antonlytics API.
"""

from typing import Dict, Any, Optional, List, Iterator
from .http_client import HTTPClient
from .exceptions import AntonlyticsError


class Agent:
    """
    Antonlytics Agent - Give your AI agent memory.
    
    Example:
        >>> from antonlytics import Agent
        >>> 
        >>> agent = Agent(
        ...     api_key="your-api-key",
        ...     project_id="your-project-id"
        ... )
        >>> 
        >>> # Ingest data - agent learns
        >>> agent.ingest("Had a call with Sarah from TechCorp about Enterprise plan")
        >>> 
        >>> # Chat with agent - agent remembers
        >>> response = agent.chat("Who should I follow up with?")
        >>> print(response["response"])
    """
    
    def __init__(
        self,
        api_key: str,
        project_id: str,
        base_url: str = "https://api.antonlytics.com"
    ):
        """
        Initialize Antonlytics Agent.
        
        Args:
            api_key: Your Antonlytics API key
            project_id: Your project/agent ID
            base_url: API base URL (default: https://api.antonlytics.com)
        """
        if not api_key:
            raise AntonlyticsError("API key is required")
        if not project_id:
            raise AntonlyticsError("Project ID is required")
            
        self.api_key = api_key
        self.project_id = project_id
        self.base_url = base_url.rstrip('/')
        self.client = HTTPClient(api_key, base_url)
    
    def ingest_triplets(self, triplets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Ingest pre-formed triplets directly — bypasses Claude extraction.

        Use this from SaaS applications when your code already knows the
        structured data (rows from a DB, parsed events, etc.) and you don't
        want to pay LLM extraction cost / latency.

        Each triplet is:
            {
              "subject":   {"type": str, "id": str, "properties": dict},
              "predicate": str,   # e.g. "PURCHASED"
              "object":    {"type": str, "id": str, "properties": dict},
              "relationship_properties": dict (optional)
            }

        Args:
            triplets: list of triplet dicts.

        Returns:
            ``{"success": bool, "event_id": str, "async": bool, "results": {...}}``
            Batches over 100 are processed asynchronously; poll
            ``Agent.ingestion_event_status(event_id)``.
        """
        if not triplets:
            raise AntonlyticsError("triplets must be a non-empty list")
        return self.client.post('/api/v1/ingest/', {
            'project_id': self.project_id,
            'triplets': triplets,
        })

    def upsert_entity(
        self,
        type: str,
        external_id: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Convenience: create or update a single entity (no relationship).

        Internally posts a self-referential triplet which the engine treats as
        an entity upsert — same code path as direct ingestion."""
        return self.ingest_triplets([{
            'subject':   {'type': type, 'id': external_id, 'properties': properties or {}},
            'predicate': 'SELF',
            'object':    {'type': type, 'id': external_id, 'properties': properties or {}},
        }])

    def add_relationship(
        self,
        source: Dict[str, Any],
        predicate: str,
        target: Dict[str, Any],
        relationship_properties: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Convenience: post a single (source --[predicate]--> target) edge.

        Both endpoints are upserted if they don't already exist."""
        return self.ingest_triplets([{
            'subject':                  source,
            'predicate':                predicate,
            'object':                   target,
            'relationship_properties':  relationship_properties or {},
        }])

    def ingest(self, text: str) -> Dict[str, Any]:
        """
        Ingest text and extract entities/relationships.
        Your agent learns from this text.
        
        Args:
            text: Natural language text (conversations, notes, emails)
            
        Returns:
            Dict with extracted entities and relationships
            
        Example:
            >>> agent.ingest('''
            ... Had a meeting with Alice Johnson from DataCorp today.
            ... She's interested in our Pro plan for 20 engineers.
            ... Follow up next Tuesday.
            ... ''')
            {
                "extracted": {
                    "entities": [
                        {"name": "Alice Johnson", "type": "Person"},
                        {"name": "DataCorp", "type": "Company"}
                    ],
                    "relationships": [...]
                },
                "created": {"entities": 2, "relationships": 1}
            }
        """
        if not text or not text.strip():
            raise AntonlyticsError("Text cannot be empty")
            
        return self.client.post('/api/v1/memory/extract/', {
            'text': text.strip(),
            'project_id': self.project_id
        })
    
    def chat(self, message: str, history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Chat with your agent. Agent has full memory context.
        Uses your system prompt + memory from knowledge graph.
        
        Args:
            message: Your question or message
            history: Optional conversation history
            
        Returns:
            Dict with agent's response and relevant entities
            
        Example:
            >>> response = agent.chat("Who should I follow up with?")
            >>> print(response["response"])
            "You should follow up with Alice from DataCorp..."
            >>> 
            >>> # Access relevant entities
            >>> for entity in response["relevant_entities"]:
            ...     print(f"{entity['name']} - {entity['type']}")
        """
        if not message or not message.strip():
            raise AntonlyticsError("Message cannot be empty")
            
        payload = {
            'message': message.strip(),
            'project_id': self.project_id
        }
        
        if history:
            payload['history'] = history
            
        return self.client.post('/api/v1/memory/chat/', payload)
    
    def get_memory(
        self,
        query: Optional[str] = None,
        *,
        max_entities: int = 10_000,
        page_size: int = 500,
    ) -> Dict[str, Any]:
        """
        Get memory context for your own agent/model.

        Two modes:
          - ``query`` provided: semantic top-K retrieval (single shot, server-ranked).
            Returns the most relevant entities and their relationships.
          - ``query=None``: enumerates the full project graph via cursor pagination,
            auto-iterating pages internally. Stops at ``max_entities`` for safety.

        Args:
            query: Optional natural language query for ranked retrieval.
            max_entities: Safety ceiling for full-graph mode (default 10000).
            page_size: Pagination page size for full-graph mode (1-1000, default 500).

        Returns:
            Dict with entities and relationships.

        Example:
            >>> # Top-K retrieval for prompt context
            >>> memory = agent.get_memory(query="What did Sarah say?")
            >>>
            >>> # Full project dump (auto-paginated)
            >>> all_memory = agent.get_memory()
            >>>
            >>> # For very large projects, stream pages:
            >>> for page in agent.iter_memory(page_size=500):
            ...     process(page)
        """
        if query:
            response = self.client.post('/api/v1/memory/query/', {
                'question': query,
                'project_id': self.project_id,
            })
            return response.get('graph_context', {})

        # Full-graph mode: auto-paginate via /memory/list/.
        entities: List[Dict[str, Any]] = []
        relationships: List[Dict[str, Any]] = []
        for page in self.iter_memory(page_size=page_size):
            entities.extend(page.get('entities', []))
            relationships.extend(page.get('relationships', []))
            if len(entities) >= max_entities:
                entities = entities[:max_entities]
                break
        return {'entities': entities, 'relationships': relationships}

    def iter_memory(self, page_size: int = 500) -> Iterator[Dict[str, Any]]:
        """
        Stream the full project graph one page at a time.

        Yields a dict ``{entities, relationships, next_cursor, has_more}`` per page.
        Iteration stops automatically when the server reports no more pages.

        Args:
            page_size: Rows per page (1-1000, default 500).

        Example:
            >>> for page in agent.iter_memory(page_size=200):
            ...     for entity in page["entities"]:
            ...         print(entity["name"])
        """
        cursor: Optional[str] = None
        while True:
            payload: Dict[str, Any] = {
                'project_id': self.project_id,
                'limit': page_size,
            }
            if cursor:
                payload['cursor'] = cursor
            page = self.client.post('/api/v1/memory/list/', payload)
            yield page
            if not page.get('has_more'):
                break
            cursor = page.get('next_cursor')
            if not cursor:
                break
    
    def set_system_prompt(self, prompt: str) -> Dict[str, Any]:
        """
        Set the system prompt for your agent.
        Defines agent behavior and personality.
        
        Args:
            prompt: System prompt text
            
        Returns:
            Dict with updated system prompt
            
        Example:
            >>> agent.set_system_prompt('''
            ... You are a helpful sales assistant.
            ... Be concise and action-oriented.
            ... Focus on follow-ups and next steps.
            ... ''')
        """
        if not prompt or not prompt.strip():
            raise AntonlyticsError("System prompt cannot be empty")
            
        return self.client.patch(
            f'/api/v1/memory/system-prompt/{self.project_id}/',
            {'system_prompt': prompt.strip()}
        )
    
    def get_system_prompt(self) -> str:
        """
        Get current system prompt.
        
        Returns:
            System prompt text
        """
        response = self.client.get(f'/api/v1/memory/system-prompt/{self.project_id}/')
        return response.get('system_prompt', '')
