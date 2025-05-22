from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse

from scripts.services.deployment_service import deployment_router
from scripts.services.image_service import image_router as image_router
from scripts.services.cont_service import container_router as cont_router
from scripts.services.vol_service import volume_router as vol_router
from scripts.services.rate_limit_service import rate_limit_router as rate_router
from scripts.services.jwt_service import auth_router as auth_router


def create_app(root_path: str = "") -> FastAPI:
    app = FastAPI(
        title="Docker Management API",
        description="APIs to manage Docker Images, Containers, and Volumes",
        version="1.0.0",
        swagger_ui_oauth2_redirect_url=f"{root_path}/docs/oauth2-redirect",
        root_path=root_path,
        docs_url=None,
        redoc_url=None,
    )

    # Fix: dynamically use request.scope['root_path'] in Swagger route
    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html(request: Request):
        current_root_path = request.scope.get("root_path", "")
        return get_swagger_ui_html(
            openapi_url=f"{current_root_path}/openapi.json",
            title="Docker Management API Docs",
            oauth2_redirect_url=f"{current_root_path}/docs/oauth2-redirect",
            swagger_ui_parameters={"persistAuthorization": True},
        )

    @app.get("/openapi.json", include_in_schema=False)
    async def custom_openapi():
        return get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )

    @app.get("/docs/oauth2-redirect", include_in_schema=False)
    async def swagger_redirect():
        return HTMLResponse(
            """
            <script>
                'use strict';
                function run () {
                    var hash = window.location.hash;
                    var message = {
                        type: "oauth2_redirect",
                        hash: hash
                    }
                    window.opener.postMessage(message, window.location.origin);
                }
                window.onload = run
            </script>
            """
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router, prefix="/auth", tags=["Authentication Operations"])
    app.include_router(rate_router, prefix="/rate-limit", tags=["Rate Limit Operations"])
    app.include_router(image_router, prefix="/images", tags=["Image Operations"])
    app.include_router(cont_router, prefix="/container", tags=["Container Operations"])
    app.include_router(vol_router, prefix="/volume", tags=["Volume Operations"])
    app.include_router(deployment_router, prefix="/deployment", tags=["Deployment Operations"])

    return app
