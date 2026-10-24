from fastapi import FastAPI

from app.core.config import get_settings

settings = get_settings()
app = FastAPI(title="HCM Lite API", version="0.1.0")


@app.get("/api/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
