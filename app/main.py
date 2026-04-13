from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import feed
from app.metrics import metrics_endpoint
from app.config import settings

app = FastAPI(title="gobig-social-api", version="0.1.0")

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


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint
    """
    return metrics_endpoint()
