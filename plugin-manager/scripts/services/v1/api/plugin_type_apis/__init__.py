from fastapi import APIRouter

from . import protocols

router = APIRouter(prefix="/plugin-services")

router.include_router(protocols.router)
