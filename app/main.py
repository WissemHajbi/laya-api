import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from laya import Router
from pydantic import BaseModel, Field


def env_list(name: str, default: str) -> list[str]:
    return [value.strip() for value in os.getenv(name, default).split(",") if value.strip()]


DEVICE = os.getenv("LAYA_DEVICE", "cpu")
PRELOAD_MODELS = env_list("LAYA_PRELOAD", "english")
MAX_LOADED = int(os.getenv("LAYA_MAX_LOADED", str(max(1, len(PRELOAD_MODELS)))) or "1")

router = Router(device=DEVICE, max_loaded=MAX_LOADED)
startup_error: str | None = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    global startup_error
    try:
        if PRELOAD_MODELS:
            router.preload(PRELOAD_MODELS)
    except Exception as exc:
        startup_error = str(exc)
        raise
    yield
    router.unload()


app = FastAPI(
    title="Local Laya API",
    version="1.0.0",
    lifespan=lifespan,
)


class PredictRequest(BaseModel):
    state: Any
    questions: dict[str, dict[str, Any]] = Field(min_length=1)
    model: str | None = None
    task: str | None = None
    lang: str | None = None


class RouteRequest(BaseModel):
    state: Any
    questions: dict[str, dict[str, Any]] = Field(default_factory=dict)
    model: str | None = None
    task: str | None = None
    lang: str | None = None


@app.get("/")
def root():
    return {"service": "laya", "docs": "/docs", "health": "/health"}


@app.get("/health")
def health():
    return {
        "status": "error" if startup_error else "ready",
        "device": DEVICE,
        "loaded_models": router.loaded,
        "startup_error": startup_error,
    }


@app.post("/route")
def route(request: RouteRequest):
    """Inspect routing without loading or running a model."""
    try:
        return router.route(
            request.state,
            request.questions,
            model=request.model,
            task=request.task,
            lang=request.lang,
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/predict")
def predict(request: PredictRequest):
    try:
        return router.predict(
            request.state,
            request.questions,
            model=request.model,
            task=request.task,
            lang=request.lang,
        )
    except (TypeError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=f"Inference failed: {exc}") from exc
