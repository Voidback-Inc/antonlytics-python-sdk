"""
Agent class for interacting with Antonlytics API.
"""

from typing import Dict, Any, Optional, List
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
    
    def get_memory(self, query: Optional[str] = None) -> Dict[str, Any]:
        """
        Get memory context for your own agent/model.
        Returns structured knowledge graph data.
        
        Args:
            query: Optional natural language query to filter context
            
        Returns:
            Dict with entities and relationships
            
        Example:
            >>> # Get all memory
            >>> memory = agent.get_memory()
            >>> 
            >>> # Use with your own model
            >>> your_model.chat(
            ...     system="You are a sales assistant",
            ...     context=memory,
            ...     message="Who to follow up?"
            ... )
        """
        if query:
            response = self.client.post('/api/v1/memory/query/', {
                'question': query,
                'project_id': self.project_id
            })
            return response.get('graph_context', {})
        else:
            # Get all memory
            response = self.client.post('/api/v1/memory/query/', {
                'question': 'What do you know?',
                'project_id': self.project_id
            })
            return response.get('graph_context', {})
    
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
