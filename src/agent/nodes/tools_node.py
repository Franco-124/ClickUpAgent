from langgraph.prebuilt import ToolNode

from tools.click_up import create_task, get_tasks, update_task, get_task_details, delete_task

_tools = [get_tasks, create_task, update_task, get_task_details, delete_task]
tools_node = ToolNode(_tools)
