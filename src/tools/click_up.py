
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
        return "Error en la comunicación con ClickUp, intenta de nuevo o dile a johan que hubo un error al usar la tool"
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return "Error tratando de ejecutar la acción, intenta de nuevo o dile a johan que hubo un error al usar la tool"
@tool
def get_tasks() -> str:
    """Fetch tasks from ClickUp."""
    try:
        response = _request("GET", f"/list/{config.CLICKUP_LIST_ID}/task")
        tasks = response.get("tasks", [])
        result = [f"[task id:{t['id']}] task name: {t['name']} — status: {t['status']['status']}" for t in tasks]

        logger.info(f"Tasks retrieved successfully: {len(tasks)} tasks found.")
        logger.info(f"Tasks details: {result}")
        if not result:
            return "Dile a johan que no se encontraron tareas en click up."
        return "\n".join(result)
    except Exception as e:
        logger.error(f"Error fetching tasks: {e}")
        return "Hubo un error al tratar de obtener las tareas, intenta de nuevo o dile a johan que hubo un error al usar la tool"


@tool
def create_task(name: str, description: str = "") -> str:
    """Crea una nueva tarea en ClickUp con el nombre y descripción indicados.
    Úsala cuando el usuario quiera agregar, crear o registrar una nueva tarea."""
    try:
        body = {"name": name, "description": description}
        response = _request("POST", f"/list/{config.CLICKUP_LIST_ID}/task", json=body)
        task_id = response.get("id")
        logger.info(f"Task created successfully. ID: {task_id}, Name: {name}")
        return f"Tarea creada exitosamente. ID: {task_id}, Nombre: {name}"
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        return "Hubo un error al tratar de crear la tarea, intenta de nuevo o dile a johan que hubo un error al usar la tool"


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
        return "Error tratando de actualizar la tarea, intenta de nuevo o dile a johan que hubo un error al usar la tool"

@tool
def get_task_details(task_id: str) -> str:
    """Obtiene toda la información detallada de una tarea específica en ClickUp, 
    incluyendo su descripción completa, etiquetas y subtareas.
    Úsala cuando necesites entender el contexto profundo de una tarea antes de modificarla."""
    try:
        response = _request("GET", f"/task/{task_id}")
        desc = response.get("description", "Sin descripción")
        tags = [tag["name"] for tag in response.get("tags", [])]
        logger.info(f"Task details retrieved successfully. ID: {task_id}, Name: {response.get('name')}")
        return f"Tarea {task_id}: {response.get('name')}\nDescripción: {desc}\nEtiquetas: {', '.join(tags) if tags else 'Ninguna'}"
    except Exception as e:
        logger.error(f"Error fetching task details: {e}")
        return "Error tratando de obtener los detalles de la tarea, intenta de nuevo o dile a johan que hubo un error al usar la tool"


@tool
def delete_task(task_id: str) -> str:
    """Usa esta tool para eliminar una tarea en clickup, siempre deberas pasar el task id , sino lo conoces
    primero debes usar get_tasks para obtener el id de la tarea que quieres eliminar.
    """
    try:
        logger.info(f"Attempting to delete task. ID: {task_id}")

        _request("DELETE", f"/task/{task_id}")
        logger.info(f"Task deleted successfully. ID: {task_id}")
        return f"Tarea {task_id} eliminada exitosamente."
    except Exception as e:
        logger.error(f"Error deleting task: {e}")
        return "Error tratando de eliminar la tarea, intenta de nuevo o dile a johan que hubo un error al usar la tool"