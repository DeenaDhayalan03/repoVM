from fastapi import APIRouter

from scripts.constants.api import APIEndPoints

from . import handler
from .api import plugin_type_apis, plugins, ui_services, git_target

router = APIRouter(prefix=APIEndPoints.v1)

router.include_router(plugins.router)
router.include_router(ui_services.router)
router.include_router(plugin_type_apis.router)
router.include_router(git_target.router)
