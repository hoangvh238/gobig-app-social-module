from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import feed
from app.routers import stories
from app.routers import potluck
from app.routers import media
from app.metrics import metrics_endpoint
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure ES index exists with proper mapping
    from app.services.es_client import ESClient

    try:
        await ESClient.ensure_index()
    except Exception as e:
        print(f"[Startup] ES index setup (non-fatal): {e}")

    yield

    # Shutdown: close clients
    await ESClient.close()


app = FastAPI(title="gobig-social-api", version="0.1.0", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers
app.include_router(feed.router, prefix="/social", tags=["social"])
app.include_router(stories.router, prefix="/social", tags=["stories"])
app.include_router(potluck.router, prefix="/social", tags=["potluck"])
app.include_router(media.router, prefix="/api", tags=["media"])


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint
    """
    return metrics_endpoint()
