import logging
import os

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from scripts.services import router

health_router = APIRouter(tags=["Healthcheck"], include_in_schema=False)


@health_router.get("/api/dynamic-proxies/healthcheck")
async def ping():
    return {"status": 200}


if os.environ.get("ENABLE_METRICS", False):
    try:
        from prometheus_fastapi_instrumentator import Instrumentator
    except ImportError:
        logging.warning("Monitoring will not be available - Install Instrumentator")
        Instrumentator = None
else:
    Instrumentator = None
app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(health_router)

if os.environ.get("ENABLE_METRICS"):
    Instrumentator().instrument(app).expose(app)
