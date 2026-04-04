from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import tools_condition

from agent.nodes.llm_node import llm_node
from agent.nodes.tools_node import tools_node
from agent.state import AgentState

# Method used to build the graph. It is called once when the module is imported.
def _build_graph():
    builder = StateGraph(AgentState)

    builder.add_node("llm", llm_node)
    builder.add_node("tools", tools_node)

    builder.add_edge(START, "llm")
    builder.add_conditional_edges("llm", tools_condition)
    builder.add_edge("tools", "llm")

    return builder.compile(checkpointer=MemorySaver())


_graph = _build_graph()


def get_graph():
    return _graph
