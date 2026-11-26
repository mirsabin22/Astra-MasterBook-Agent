from fastapi import FastAPI

from .read import router as read_router
from .write import router as write_router

app = FastAPI(title="Masterbook Agent API")
app.include_router(read_router)
app.include_router(write_router)


@app.get("/health")
def health():
    return {"ok": True}