
import httpx
import logging
from langchain_core.tools import tool


from config.environment import config

# set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def _headers() -> dict:
    """Generate headers for ClickUp API requests."""
    return {
        "Authorization": config.CLICK_UP_API_TOKEN,
    }

def _request(method: str, endpoint: str, **kwargs) -> dict:
    """Make an HTTP request to the ClickUp API."""
    url = f"{config.CLICK_UP_BASE_URL}{endpoint}"
    headers = _headers()
    try:
        response = httpx.request(method, url, headers=headers, **kwargs)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
        raise e
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        raise e
@tool
def get_tasks() -> str:
    """Fetch tasks from ClickUp."""
    try:
        response = _request("GET", f"/list/{config.CLICKUP_LIST_ID}/task")
        tasks = response.get("tasks", [])
        result = [f"[task id:{t['id']}] task name: {t['name']} — status: {t['status']['status']}" for t in tasks]
        return "\n".join(result)
    except Exception as e:
        logger.error(f"Error fetching tasks: {e}")
        raise e


@tool
def create_task(name: str, description: str = "") -> str:
    """Crea una nueva tarea en ClickUp con el nombre y descripción indicados.
    Úsala cuando el usuario quiera agregar, crear o registrar una nueva tarea."""
    try:
        body = {"name": name, "description": description}
        response = _request("POST", f"/list/{config.CLICKUP_LIST_ID}/task", json=body)
        task_id = response.get("id")
        return f"Tarea creada exitosamente. ID: {task_id}, Nombre: {name}"
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        raise e


@tool
def update_task(task_id: str, name: str = None, description: str = None, status: str = None) -> str:
    """Actualiza una tarea existente en ClickUp. Puede cambiar el nombre, la descripción
    y/o el estado (valores válidos: 'Open', 'in progress', 'complete').
    Úsala cuando el usuario quiera modificar, renombrar, completar o cambiar el estado
    de una tarea. El task_id se obtiene primero con get_tasks."""
    try:
        body = {
            k: v for k, v in
            {"name": name, "description": description, "status": status}.items()
            if v is not None
        }
        _request("PUT", f"/task/{task_id}", json=body)
        return f"Tarea {task_id} actualizada exitosamente."
    except Exception as e:
        logger.error(f"Error updating task: {e}")
        raise e