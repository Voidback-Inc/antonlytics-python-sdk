# Antonlytics Python SDK

Memory for AI Agents - Simple natural language SDK.

[![PyPI version](https://badge.fury.io/py/antonlytics.svg)](https://badge.fury.io/py/antonlytics)
[![Python Versions](https://img.shields.io/pypi/pyversions/antonlytics.svg)](https://pypi.org/project/antonlytics/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Installation

```bash
pip install antonlytics
```

## Quick Start

```python
from antonlytics import Agent

# Initialize agent
agent = Agent(
    api_key="your-api-key",
    project_id="your-project-id"
)

# Ingest - agent learns from natural language
agent.ingest("""
Had a call with Sarah Johnson from TechCorp today.
She's interested in our Enterprise plan for 50 users.
Follow up next Tuesday.
""")

# Chat - agent remembers and responds
response = agent.chat("Who should I follow up with?")
print(response["response"])
# => "You should follow up with Sarah Johnson from TechCorp..."
```

## Features

- **Natural Language Ingestion** - No complex entity creation, just plain English
- **AI-Powered Chat** - Chat with your agent using our model + your memory
- **Memory Access** - Get structured memory for your own AI model
- **System Prompts** - Configure agent behavior and personality
- **Simple API** - 3 lines of code to get started

## Two Usage Options

### Option 1: Use Our Model

Full-service AI with your system prompt + memory:

```python
# We handle everything
response = agent.chat("Who should I follow up with?")
print(response["response"])
```

### Option 2: Use Your Model

Just get memory context for your own model:

```python
# Get memory
memory = agent.get_memory()

# Use with your model (OpenAI, Anthropic, etc.)
from openai import OpenAI
client = OpenAI()

response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": "You are a sales assistant"},
        {"role": "system", "content": f"Memory: {memory}"},
        {"role": "user", "content": "Who to follow up?"}
    ]
)
```

## Documentation

### Agent Class

#### `__init__(api_key, project_id, base_url=None)`

Initialize the agent.

**Parameters:**
- `api_key` (str): Your Antonlytics API key
- `project_id` (str): Your project/agent ID
- `base_url` (str, optional): API base URL

#### `ingest(text: str) -> dict`

Ingest natural language text and extract entities/relationships.

**Parameters:**
- `text` (str): Natural language text (conversations, notes, emails)

**Returns:**
- dict with extracted entities and relationships

**Example:**
```python
result = agent.ingest("Customer Alice bought Laptop Pro for $999")
print(result["created"])  # {"entities": 2, "relationships": 1}
```

#### `chat(message: str, history: list = None) -> dict`

Chat with your agent. Uses system prompt + full memory context.

**Parameters:**
- `message` (str): Your question or message
- `history` (list, optional): Conversation history

**Returns:**
- dict with response and relevant entities

**Example:**
```python
response = agent.chat("Who bought laptops?")
print(response["response"])
print(response["relevant_entities"])
```

#### `get_memory(query: str = None) -> dict`

Get structured memory for your own AI model.

**Parameters:**
- `query` (str, optional): Natural language query to filter memory

**Returns:**
- dict with entities and relationships

**Example:**
```python
memory = agent.get_memory("laptop purchases")
# Use with your own model
```

#### `set_system_prompt(prompt: str) -> dict`

Configure agent behavior and personality.

**Parameters:**
- `prompt` (str): System prompt text

**Example:**
```python
agent.set_system_prompt("""
You are a helpful sales assistant.
Be concise and action-oriented.
Focus on follow-ups and next steps.
""")
```

#### `get_system_prompt() -> str`

Get current system prompt.

**Returns:**
- str: System prompt text

## Error Handling

```python
from antonlytics import Agent, AntonlyticsError, APIError, AuthenticationError

try:
    agent = Agent(api_key="invalid", project_id="test")
    agent.chat("Hello")
except AuthenticationError as e:
    print(f"Auth error: {e}")
except APIError as e:
    print(f"API error: {e.status_code} - {e}")
except AntonlyticsError as e:
    print(f"Error: {e}")
```

## Complete Example

```python
from antonlytics import Agent

# Initialize
agent = Agent(
    api_key="your-api-key",
    project_id="your-project-id"
)

# Set behavior
agent.set_system_prompt("""
You are a sales assistant.
Focus on follow-ups and next steps.
""")

# Ingest multiple conversations
agent.ingest("""
Call with Mike Rodriguez from StartupXYZ.
He's the founder. Looking at our API for their mobile app.
Has 100K users. Wants custom pricing.
Send proposal by Friday.
""")

agent.ingest("""
Email from Sarah Chen at BigCorp.
VP of Engineering. Interested in Enterprise.
Team of 200 developers. Budget discussion next week.
""")

# Query memory
response = agent.chat("What are my top priorities this week?")
print(response["response"])

# Get all contacts
response = agent.chat("List all people I've talked to")
for entity in response["relevant_entities"]:
    if entity["type"] == "Person":
        print(f"- {entity['name']}")
```

## Requirements

- Python >= 3.8
- requests >= 2.28.0

## Development

```bash
# Clone repository
git clone https://github.com/Voidback-Inc/antonlytics-python-sdk
cd antonlytics-python-sdk

# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black .

# Type check
mypy antonlytics
```

## Links

- [Documentation](https://antonlytics.com/docs/python-sdk)
- [API Reference](https://antonlytics.com/docs/api)
- [GitHub](https://github.com/Voidback-Inc/antonlytics-python-sdk)
- [Website](https://antonlytics.com)

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support

- Email: support@antonlytics.com
- Documentation: https://antonlytics.com/docs
- Issues: https://github.com/Voidback-Inc/antonlytics-python-sdk/issues
