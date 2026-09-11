"""Minimal FastAPI application owned by V1-C01."""

from fastapi import FastAPI

from traid import __version__
from traid.config import load_settings

settings = load_settings()
app = FastAPI(title="TraID", version=__version__)


@app.get("/health")
def health() -> dict[str, str]:
    """Return a deterministic process health response."""

    return {
        "status": "ok",
        "service": "traid",
        "version": __version__,
        "environment": settings.environment,
    }
