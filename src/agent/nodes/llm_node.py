from langchain_core.messages import SystemMessage
from langchain_groq import ChatGroq

from config.environment import config
from agent.state import AgentState
from tools.click_up import create_task, get_tasks, update_task

_tools = [get_tasks, create_task, update_task]
_llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=config.GROQ_API_KEY,
).bind_tools(_tools)

_system_prompt = SystemMessage(content="""Eres el asistente personal de productividad de Johan Franco.
Tu único propósito es ayudarlo a gestionar sus tareas en ClickUp de forma eficiente.
Siempre responde en español, de manera clara y concisa.
Cuando necesites el ID de una tarea para actualizarla o completarla, primero llama a get_tasks.""")


def llm_node(state: AgentState) -> dict:
    messages = [_system_prompt] + state["messages"]
    response = _llm.invoke(messages)
    return {"messages": [response]}
