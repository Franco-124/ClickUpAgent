# SPEC.md — ClickUp Agent MVP

## 1. Visión general

Agente de productividad personal que expone un endpoint HTTP `POST /chat`. Recibe mensajes en lenguaje natural (español), decide qué operación de ClickUp ejecutar, y responde con el resultado. Mantiene memoria conversacional por sesión mientras el servidor esté activo.

---

## 2. Stack técnico

| Componente | Librería / Versión |
|---|---|
| Python | 3.13 (según `.python-version`) |
| LLM | `langchain-google-genai` → `gemini-2.0-flash` |
| Orquestación | `langgraph` — `StateGraph` |
| HTTP API | `fastapi` + `uvicorn` |
| HTTP cliente | `httpx` |
| Env vars | `python-dotenv` |
| Tool decorador | `langchain-core` → `@tool` |

**Dependencias a agregar en `pyproject.toml`:**
- `langchain-google-genai>=2.0.0`
- `fastapi>=0.115.0`
- `uvicorn>=0.34.0`

---

## 3. Variables de entorno

Archivo: `src/.env`

| Variable | Descripción |
|---|---|
| `CLICK_UP_API_TOKEN` | Personal token ClickUp (`pk_...`) |
| `CLICKUP_LIST_ID` | ID de la lista principal |
| `CLICK_UP_BASE_URL` | Base URL de la API (`https://api.clickup.com/api/v2`) |
| `GEMINI_API_KEY` | API key de Google Gemini |

**`config/environment.py` no requiere cambios** — `GEMINI_API_KEY` ya está presente.

---

## 4. Estructura de archivos final

```
ClickUpAgent/
├── SPEC.md
├── main.py                          # entrypoint: uvicorn app
├── pyproject.toml
├── src/
│   ├── config/
│   │   ├── __init__.py
│   │   └── environment.py           # ✅ ya existe — sin cambios
│   ├── tools/
│   │   ├── __init__.py              # ✅ ya existe
│   │   └── click_up.py              # ✅ get_tasks + agregar create_task, update_task
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── state.py                 # AgentState TypedDict
│   │   ├── graph.py                 # StateGraph: nodos + edges + compilación
│   │   └── nodes/
│   │       ├── __init__.py
│   │       ├── llm_node.py          # nodo: LLM decide / responde
│   │       └── tools_node.py        # nodo: ejecuta tools
│   └── api/
│       ├── __init__.py
│       └── routes.py                # POST /chat
```

---

## 5. Especificación por componente

### 5.1 `src/tools/click_up.py`

Agrega dos tools nuevas al archivo existente.

#### `create_task(name: str, description: str = "") -> str`
- **Método:** `POST /list/{CLICKUP_LIST_ID}/task`
- **Body JSON:** `{"name": name, "description": description}`
- **Retorna:** string con confirmación y el `id` de la task creada.
- **Docstring (prompt para el LLM):** "Crea una nueva tarea en ClickUp con el nombre y descripción indicados. Úsala cuando el usuario quiera agregar, crear o registrar una nueva tarea."

#### `update_task(task_id: str, name: str = None, description: str = None, status: str = None) -> str`
- **Método:** `PUT /task/{task_id}`
- **Body JSON:** solo los campos que no sean `None` (evitar sobrescribir con vacíos)
- **Retorna:** string con confirmación del `id` actualizado.
- **Docstring (prompt para el LLM):** "Actualiza una tarea existente en ClickUp. Puede cambiar el nombre, la descripción y/o el estado. Úsala cuando el usuario quiera modificar, renombrar, completar o cambiar el estado de una tarea. El task_id se obtiene primero con get_tasks."

**Statuses válidos en ClickUp:** `"Open"`, `"in progress"`, `"complete"` (el LLM deberá mapear intenciones del usuario a estos valores).

---

### 5.2 `src/agent/state.py`

```python
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
```

- Usa `Annotated` con el reducer `add_messages` de LangGraph para acumular el historial correctamente.
- `messages` es la única clave de estado — el historial completo se pasa al LLM en cada turno.

---

### 5.3 `src/agent/nodes/llm_node.py`

**Responsabilidad:** invocar el LLM con el historial actual y las tools ligadas.

- Instancia `ChatGoogleGenerativeAI(model="gemini-2.0-flash")` — instancia única a nivel de módulo.
- Las tools disponibles: `[get_tasks, create_task, update_task]`.
- El LLM se inicializa con `.bind_tools(tools)`.
- **Función del nodo:** `llm_node(state: AgentState) -> dict`
  - Invoca `llm.invoke(state["messages"])`
  - Retorna `{"messages": [response]}`

---

### 5.4 `src/agent/nodes/tools_node.py`

**Responsabilidad:** ejecutar la tool que el LLM seleccionó.

- Usa `ToolNode` de LangGraph: `ToolNode(tools=[get_tasks, create_task, update_task])`.
- Se expone como `tools_node = ToolNode(tools)` — instancia lista para registrar en el grafo.

---

### 5.5 `src/agent/graph.py`

**Responsabilidad:** definir y compilar el grafo del agente con memoria por sesión.

#### Nodos
| Nombre | Función |
|---|---|
| `"llm"` | `llm_node` |
| `"tools"` | `tools_node` |

#### Edges
```
START → "llm"
"llm" → tools_condition:
    si hay tool_calls → "tools"
    si no hay tool_calls → END
"tools" → "llm"
```

#### Memoria de sesión
- `MemorySaver` de LangGraph como `checkpointer`.
- El grafo se compila con `graph.compile(checkpointer=MemorySaver())`.
- **Función pública:** `get_graph() -> CompiledGraph` — retorna la instancia compilada (singleton).

#### `tools_condition`
Usa `tools_condition` importado de `langgraph.prebuilt` — no reimplementar.

---

### 5.6 `src/api/routes.py`

**Responsabilidad:** exponer el endpoint HTTP y gestionar la sesión.

#### Modelos Pydantic
```python
class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):
    response: str
```

#### Endpoint `POST /chat`
- Recibe `ChatRequest`.
- Invoca el grafo con:
  ```python
  config = {"configurable": {"thread_id": request.session_id}}
  result = graph.invoke(
      {"messages": [HumanMessage(content=request.message)]},
      config=config
  )
  ```
- Extrae el último mensaje de `result["messages"]` y retorna su `.content`.
- Retorna `ChatResponse(response=last_message.content)`.

#### Router
- `APIRouter` con prefix `""` (sin prefix).
- El router se llama `router` para importarlo en `main.py`.

---

### 5.7 `main.py`

**Responsabilidad:** inicializar FastAPI y registrar el router.

```python
app = FastAPI(title="ClickUp Agent")
app.include_router(router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

- El `sys.path.append` existente se mantiene para resolver imports desde `src/`.

---

## 6. Flujo de una request

```
POST /chat {"session_id": "abc", "message": "¿qué tareas tengo?"}
    │
    ▼
routes.py → graph.invoke(HumanMessage, thread_id="abc")
    │
    ▼
llm_node → Claude analiza el mensaje → decide llamar get_tasks
    │
    ▼
tools_node → get_tasks() → "Tarea 1 — open\nTarea 2 — complete"
    │
    ▼
llm_node → Claude genera respuesta en español con las tasks
    │
    ▼
routes.py → retorna {"response": "Tenés 2 tareas: ..."}
```

---

## 7. Orden de implementación

1. `pyproject.toml` — agregar `langchain-google-genai`, `fastapi` y `uvicorn`
2. `src/tools/click_up.py` — agregar `create_task` y `update_task`
4. `src/agent/state.py` — nuevo archivo
5. `src/agent/nodes/llm_node.py` — nuevo archivo
6. `src/agent/nodes/tools_node.py` — nuevo archivo
7. `src/agent/graph.py` — nuevo archivo
8. `src/api/routes.py` — nuevo archivo
9. `main.py` — reemplazar contenido actual

---

## 8. Restricciones y reglas

- `tools/` no importa de `agent/` ni de `api/`.
- `agent/` no importa de `api/`.
- Headers de ClickUp siempre se generan con `_headers()` en tiempo de ejecución.
- Cada tool maneja sus propios errores con `raise_for_status()` (ya implementado en `_request()`).
- El LLM es instancia de módulo (se crea una vez, no por request).
- El grafo es singleton — se compila una vez al iniciar la app.
- `MemorySaver` persiste en memoria del proceso — se pierde al reiniciar.
