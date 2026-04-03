from fastapi import APIRouter
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from agent.graph import get_graph

router = APIRouter()


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    response: str


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    graph = get_graph()
    config = {"configurable": {"thread_id": request.session_id}}
    result = graph.invoke(
        {"messages": [HumanMessage(content=request.message)]},
        config=config,
    )
    last_message = result["messages"][-1]
    return ChatResponse(response=last_message.content)
