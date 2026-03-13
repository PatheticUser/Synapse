import os
import sqlite3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from research_agent import create_research_agent
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_core.messages import HumanMessage

# Ensure checkpoints directory exists
os.makedirs("checkpoints", exist_ok=True)

app = FastAPI(title="Research AI Agent API")

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str
    session_id: str = "default"

class QueryResponse(BaseModel):
    answer: str
    session_id: str

# Use a raw sqlite connection with check_same_thread=False for FastAPI thread safety
conn = sqlite3.connect("checkpoints/checkpoints.db", check_same_thread=False)
memory = SqliteSaver(conn)
agent_executor = create_research_agent(checkpointer=memory)

@app.post("/research", response_model=QueryResponse)
async def research(request: QueryRequest):
    try:
        # Invoke the agent with thread_id for automatic history management
        config = {"configurable": {"thread_id": request.session_id}}
        
        # Handle Human-in-the-Loop approval
        state_snapshot = agent_executor.get_state(config)
        
        if state_snapshot.next and request.query.strip().lower() in ["approve", "yes", "y", "proceed", "go ahead"]:
            # LangChain HumanInTheLoopMiddleware requires a specific dictionary format for the resume payload
            # We need to provide a decision for every interrupted tool call
            # We can extract the number of blocked tools from the interrupt payload
            interrupt_payload = state_snapshot.tasks[0].interrupts[0].value if state_snapshot.tasks and state_snapshot.tasks[0].interrupts else {}
            action_requests = interrupt_payload.get("action_requests", [])
            decisions = [{"type": "approve"} for _ in action_requests]
            
            from langgraph.types import Command
            response = agent_executor.invoke(Command(resume={"decisions": decisions}), config=config)
        elif state_snapshot.next:
            # If the user answered anything else but yes while paused, we reject the tool execution
            interrupt_payload = state_snapshot.tasks[0].interrupts[0].value if state_snapshot.tasks and state_snapshot.tasks[0].interrupts else {}
            action_requests = interrupt_payload.get("action_requests", [])
            decisions = [{"type": "reject", "message": request.query} for _ in action_requests]
            
            from langgraph.types import Command
            response = agent_executor.invoke(Command(resume={"decisions": decisions}), config=config)
        else:
            # Normal execution with new user input
            response = agent_executor.invoke(
                {"messages": [HumanMessage(content=request.query)]},
                config=config
            )
        
        # Get the latest message from the agent
        latest_message = response["messages"][-1]
        
        # Check if the agent paused for tool execution (HITL)
        # LangGraph returns AIMessage with tool_calls and empty content
        if hasattr(latest_message, 'tool_calls') and latest_message.tool_calls:
            answer = "[Human-in-the-Loop] Agent paused to request your approval to run tools:\n"
            for tc in latest_message.tool_calls:
                answer += f"- **{tc['name']}**: `{tc['args']}`\n"
            answer += "\nReply with 'approve' to execute these tools, or reply with new instructions to change course."
        else:
            answer = latest_message.content
        
        return QueryResponse(answer=answer, session_id=request.session_id)
        
    except Exception as e:
        print(f"Server Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history/{session_id}")
async def get_history(session_id: str):
    try:
        # Get state from the agent checkpointer
        config = {"configurable": {"thread_id": session_id}}
        state = agent_executor.get_state(config)
        
        messages = state.values.get("messages", [])
        
        formatted_history = []
        for msg in messages:
            role = "user" if isinstance(msg, HumanMessage) else "agent"
            # Skip tool messages in the history for the frontend
            if role == "agent" and not msg.content:
                continue
            formatted_history.append({"role": role, "content": msg.content})
        
        return {"history": formatted_history}
    except Exception:
        return {"history": []}

@app.delete("/history/{session_id}")
async def clear_history(session_id: str):
    # For now, we'll just acknowledge or we could try to wipe the state
    return {"message": "History clearing not fully implemented for checkpointer, but session persists."}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
