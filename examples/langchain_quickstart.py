"""
LangChain + Antonlytics quickstart.

Install:
    pip install antonlytics[langchain] langchain langchain-anthropic

Run:
    export ANTONLYTICS_API_KEY=...
    export ANTONLYTICS_PROJECT_ID=...
    export ANTHROPIC_API_KEY=...
    python examples/langchain_quickstart.py
"""
import os

from antonlytics import Agent
from antonlytics.integrations.langchain import AntonlyticsMemory

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains import ConversationChain


def main() -> None:
    agent = Agent(
        api_key=os.environ["ANTONLYTICS_API_KEY"],
        project_id=os.environ["ANTONLYTICS_PROJECT_ID"],
    )

    memory = AntonlyticsMemory(agent=agent, memory_key="history", input_key="input")

    llm = ChatAnthropic(model="claude-sonnet-4-5", temperature=0)

    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a helpful assistant. Use the prior knowledge below when relevant.\n\n"
         "{history}"),
        ("human", "{input}"),
    ])

    chain = ConversationChain(llm=llm, prompt=prompt, memory=memory, input_key="input")

    # Teach it something.
    chain.invoke({"input": "I had a sales call with Sarah from TechCorp about Enterprise pricing."})

    # Ask it back with no keyword overlap. Hybrid retrieval should still pull Sarah/TechCorp.
    out = chain.invoke({"input": "Anyone I should circle back with on a deal?"})
    print(out["response"])


if __name__ == "__main__":
    main()
