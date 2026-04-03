import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

import uvicorn
from fastapi import FastAPI

from api.routes import router

app = FastAPI(title="ClickUp Agent")
app.include_router(router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
