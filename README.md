# Synapse AI - Research Agent 

Synapse AI is an advanced, production-ready Research Agent API powered by **LangChain** and **LangGraph Checkpointing**. It is designed to synthesize information from multiple disparate sources—including the Web, Wikipedia, arXiv, and YouTube—while safely executing Python code to answer complex analytical queries.

Built with a modern architecture, Synapse AI natively supports **Human-in-the-Loop (HITL)** workflows, persistent session memory, and streaming-capable tool execution.

---

## Architecture Stack

*   **Backend Framework:** FastAPI
*   **Agent Logic:** `langchain.agents.create_agent`
*   **Routing & Middleware:** 
    *   `TodoListMiddleware` (for complex task breakdown)
    *   `HumanInTheLoopMiddleware` (for securing sensitive tools)
*   **State Persistence:** `langgraph.checkpoint.sqlite.SqliteSaver` (Thread-safe)
*   **Frontend:** React (communicates via CORS-enabled REST API)
*   **LLM Model:** Ollama (`minimax-m2.5:cloud` or user's preferred choice)

Unlike older `create_react_agent` approaches, Synapse AI utilizes LangChain's latest `create_agent` middleware pipelines, allowing seamless interruptions for human approval without complex custom graph manipulations.

---

## Key Features

*   **Multi-Source Synthesis:** Leverages cutting-edge tools to answer comprehensive research queries:
    *   **Tavily Search:** Real-time web search with automatic API key rotation to bypass rate limits.
    *   **Wikipedia:** Encyclopedia lookups for factual grounding.
    *   **arXiv:** Deep academic paper research.
    *   **YouTube Search:** Video transcript and metadata retrieval.
*   **Code Execution Engine:** Uses a built-in Python REPL (`python_tool`) for mathematical calculations, data analysis, and logical reasoning.
*   **Human-In-The-Loop (HITL) Security:** The agent is configured to ask for your explicit approval before executing its tools (such as Python REPL or web searches). The backend pauses execution and waits for human approval from the frontend before proceeding, giving you full control over every action.
*   **Persistent Sessions (Memory):** Automatically stores user conversations and agent tool-call history leveraging `SqliteSaver`. Sessions can be resumed seamlessly at any point.

---

## Prerequisites

Before you begin, ensure you have the following installed:

*   **Python:** Version 3.11 or higher.
*   **Node.js:** For running the React frontend workspace.
*   **uv:** Fast Python package installer and resolver ([GitHub - astral-sh/uv](https://github.com/astral-sh/uv)).
*   **Ollama:** Running locally with the target model downloaded (e.g., `ollama run minimax-m2.5:cloud`).

---

## Setup & Configuration

### 1. Install Dependencies

Ensure your virtual environment is active, then install the required Python dependencies specified in `pyproject.toml`:

```bash
uv sync
```

### 2. Configure API Keys

Create a `tavily_api_keys.json` file in the root directory. This file should contain a JSON array with your Tavily API key to enable web searches.

```json
[
  "tvly-YOUR_API_KEY"
]
```

---

## Running the Application

To launch the complete stack (both the FastAPI backend and the React frontend) simultaneously, use the provided Windows batch script:

```bat
run_app.bat
```

**What this does:**
1. Starts the React Frontend dev server on `http://localhost:5173`.
2. Activates the Python virtual environment via `uv run` and starts the FastAPI Backend on `http://localhost:8000`.

---

## API Endpoints Reference

The FastAPI backend exposes the following REST endpoints for frontend integration:

### Main Interaction
*   **`POST /research`**
    *   **Description:** The primary endpoint for querying the agent.
    *   **Payload:** `{"query": "your user input or HITL decision", "session_id": "unique-uuid"}`
    *   **Behavior:** If the agent triggers a HITL middleware interrupt, it will return a specialized prompt asking for approval. Sending `{query: "approve"}` or `{query: "reject"}` back to this endpoint will resume the workflow.

### History Management
*   **`GET /history/{session_id}`**
    *   **Description:** Retrieves the chat history for a given session from the SQLite Checkpointer, filtering out raw internal tool-call payloads to keep the UI clean.
*   **`DELETE /history/{session_id}`**
    *   **Description:** Placeholder endpoint for future history/state wiping functionalities. Currently acknowledges the request while letting the checkpointer maintain persistence.

---

## Project Structure Highlights

*   **`research_agent.py`:** Contains the core LangChain agent definition, complete with the custom tools, system prompts, and middleware configurations.
*   **`main.py`:** The FastAPI server that wraps the agent in web endpoints, handles thread-safe SQLite checkpointing, and dynamically routes HITL approvals/rejections based on graph states.
*   **`checkpoints/checkpoints.db`:** The auto-generated SQLite database used by `SqliteSaver` to persist agent tracking and thread states.
*   **`run_app.bat`:** The execution script for starting the dual-stack architecture.
