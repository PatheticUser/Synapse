"""
Research AI Agent

A LangChain-based AI agent for conducting research using web search,
Wikipedia, arXiv academic papers, and YouTube.
"""

import json
import warnings
from datetime import datetime
from typing import List, Optional

from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain.agents import create_agent
from langchain.agents.middleware import TodoListMiddleware, HumanInTheLoopMiddleware
from langgraph.checkpoint.sqlite import SqliteSaver

# LangChain Community Tools
from langchain_community.tools import (
    WikipediaQueryRun,
    ArxivQueryRun,
    YouTubeSearchTool
)
from langchain_tavily import TavilySearch
from langchain_community.utilities import (
    WikipediaAPIWrapper,
    ArxivAPIWrapper
)
from langchain_community.utilities.tavily_search import TavilySearchAPIWrapper

# LangChain Experimental (for Python REPL)
from langchain_experimental.utilities import PythonREPL

# Model
from langchain_ollama import ChatOllama

# Suppress BeautifulSoup warnings from the upstream wikipedia package
warnings.filterwarnings("ignore", category=UserWarning, module='wikipedia')

# --- TAVILY API KEY SWITCHER ---

class TavilyKeySwitcher:
    def __init__(self, keys_path: str = "tavily_api_keys.json"):
        self.keys_path = keys_path
        self.keys = self.load_keys()
        self.current_index = 0

    def load_keys(self) -> List[str]:
        try:
            with open(self.keys_path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading Tavily keys: {e}")
            return []

    def get_current_key(self) -> Optional[str]:
        if not self.keys:
            return None
        return self.keys[self.current_index]

    def switch_key(self):
        self.current_index = (self.current_index + 1) % len(self.keys)
        print(f"Switched to Tavily API key index: {self.current_index}")

# Initialize key switcher
key_switcher = TavilyKeySwitcher()

# Custom Tavily Tool with Key Switching
@tool
def tavily_search(query: str) -> str:
    """
    Search the web for current information, news, and articles using Tavily.
    Use this when you need up-to-date information.
    Input should be a search query.
    """
    import os
    max_retries = len(key_switcher.keys)
    for _ in range(max_retries):
        api_key = key_switcher.get_current_key()
        if not api_key:
            return "No Tavily API keys available."
        
        try:
            # Force the API key into the environment for TavilySearch to pick up natively
            os.environ["TAVILY_API_KEY"] = api_key
            search = TavilySearch()
            # Use invoke to prevent .run() deprecation warnings
            return str(search.invoke(query))
        except Exception as e:
            if "rate limit" in str(e).lower() or "429" in str(e) or "unauthorized" in str(e).lower() or "missing api key" in str(e).lower():
                key_switcher.switch_key()
                continue
            return f"Tavily Search Error: {e}"
    
    return "All Tavily API keys have hit their rate limits or are invalid."

# --- ADDITIONAL TOOLS ---

# Wikipedia
wiki_wrapper = WikipediaAPIWrapper(top_k_results=2, doc_content_chars_max=2000)
wiki_tool = WikipediaQueryRun(
    api_wrapper=wiki_wrapper,
    name="wikipedia",
    description="Query Wikipedia for encyclopedia articles. Best for factual information."
)

# Arxiv
arxiv_wrapper = ArxivAPIWrapper(top_k_results=3)
arxiv_tool = ArxivQueryRun(
    api_wrapper=arxiv_wrapper,
    name="arxiv",
    description="Search arXiv for academic papers. Best for technical and scholarly research."
)

# YouTube
youtube_tool = YouTubeSearchTool()

# Python REPL
python_repl = PythonREPL()
@tool
def python_tool(code: str) -> str:
    """
    Execute python code to solve math problems, data analysis, or general programming tasks.
    Input should be a valid python string.
    """
    try:
        return python_repl.run(code)
    except Exception as e:
        return f"Python Error: {e}"


@tool
def get_current_datetime() -> str:
    """Get the current date and time."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

tools = [
    tavily_search,
    wiki_tool, 
    arxiv_tool, 
    youtube_tool, 
    python_tool, 
    get_current_datetime
]

SYSTEM_RESEARCH_PROMPT = """You are a Research AI Agent, an expert at finding and synthesizing information.

Your capabilities:
- Search the web for current information using tavily_search.
- Look up factual information on Wikipedia.
- Find academic papers on arXiv.
- Search for videos on YouTube.
- Execute Python code for calculations or data analysis.
- Get the current datetime.

Guidelines:
1. Use the most appropriate tool for the query.
2. For factual questions, start with Wikipedia.
3. For current events, use tavily_search.
4. Synthesize information from multiple sources.
5. Provide clear, concise answers with source attribution.
6. For complex queries, use your built-in To-Do list tools to break the task down into a plan and mark tasks as completed.
"""

def create_research_agent(checkpointer=None):
    """Create a research agent with LangGraph/LangChain."""
    llm = ChatOllama(
        model="minimax-m2.5:cloud", # Keeps user's preferred model
        temperature=0.7
    )

    # Configure Human-in-the-Loop to ask for human approval before executing ANY tool
    hitl_config = {
        t.name: {"allowed_decisions": ["approve", "reject"]} 
        for t in tools
    }

    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=SYSTEM_RESEARCH_PROMPT,
        checkpointer=checkpointer,
        middleware=[
            TodoListMiddleware(),
            HumanInTheLoopMiddleware(interrupt_on=hitl_config)
        ]
    )

    return agent

def main():
    """Interactive CLI for the Research AI Agent."""
    print("Research AI Agent (Tavily Enhanced + HitL + Persistence)")
    print("=" * 40)
    
    import os
    import sqlite3
    os.makedirs("checkpoints", exist_ok=True)
    
    # Initialize SQLite checkpointer using thread-safe connection string
    conn = sqlite3.connect("checkpoints/checkpoints.db", check_same_thread=False)
    memory = SqliteSaver(conn)
    
    agent = create_research_agent(checkpointer=memory)
    config = {"configurable": {"thread_id": "cli_session"}}

    while True:
        try:
            user_input = input("You: ").strip()
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break

        if not user_input or user_input.lower() in ("quit", "exit", "q"):
            print("\nGoodbye!")
            break

        try:
            state_snapshot = agent.get_state(config)
            if state_snapshot.next and not user_input:
                # If just pressed enter, try to resume the interrupted graph!
                from langgraph.types import Command
                interrupt_payload = state_snapshot.tasks[0].interrupts[0].value if state_snapshot.tasks and state_snapshot.tasks[0].interrupts else {}
                action_requests = interrupt_payload.get("action_requests", [])
                decisions = [{"type": "approve"} for _ in action_requests]
                
                print("\nAgent: ", end="", flush=True)
                for chunk in agent.stream(Command(resume={"decisions": decisions}), config=config, stream_mode="messages"):
                    if isinstance(chunk, tuple) and hasattr(chunk[0], "content") and chunk[0].content:
                        print(chunk[0].content, end="", flush=True)
                print()
            elif state_snapshot.next and user_input:
                from langgraph.types import Command
                interrupt_payload = state_snapshot.tasks[0].interrupts[0].value if state_snapshot.tasks and state_snapshot.tasks[0].interrupts else {}
                action_requests = interrupt_payload.get("action_requests", [])
                decisions = [{"type": "reject", "message": user_input} for _ in action_requests]
                
                print("\nAgent: ", end="", flush=True)
                for chunk in agent.stream(Command(resume={"decisions": decisions}), config=config, stream_mode="messages"):
                    if isinstance(chunk, tuple) and hasattr(chunk[0], "content") and chunk[0].content:
                        print(chunk[0].content, end="", flush=True)
                print()
            else:
                # If there's input, invoke with new message
                print("\nAgent: ", end="", flush=True)
                for chunk in agent.stream(
                    {"messages": [HumanMessage(content=user_input)]},
                    config=config,
                    stream_mode="messages"
                ):
                    if isinstance(chunk, tuple) and hasattr(chunk[0], "content") and chunk[0].content:
                        print(chunk[0].content, end="", flush=True)
                print()
                
            # Check if it was interrupted for Human-in-the-Loop
            state_snapshot = agent.get_state(config)
            if state_snapshot.next:
                # The agent wants to execute a tool (HITL)
                messages = state_snapshot.values.get("messages", [])
                latest = messages[-1] if messages else None
                if latest and hasattr(latest, 'tool_calls') and latest.tool_calls:
                    print("\n[HITL Middleware] Agent wants to call tools:")
                    for tc in latest.tool_calls:
                        print(f"  - {tc['name']}: {tc['args']}")
                    print("\nPress Enter to approve, or type a message to deny/steer.")
                else:
                    print("\n[HITL Middleware] Agent paused execution. Press Enter to continue.")
            else:
                # Finished executing - already streamed, do nothing special here
                pass
            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()