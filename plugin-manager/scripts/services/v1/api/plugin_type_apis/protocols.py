import logging
from pathlib import Path

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import FileResponse
from ut_security_util import MetaInfoSchema

from scripts.constants import APIEndPoints
from scripts.core.engines.plugin_deployment_engines.protocols import DeploymentEngine
from scripts.services.v1.schemas import DefaultFailureResponse, DefaultResponse

router = APIRouter(prefix=APIEndPoints.protocols_base, tags=["v1 | Plugin Protocols"])


@router.post(APIEndPoints.plugin_protocol_validate)
async def validate_protocol(user_details: MetaInfoSchema, files: list[UploadFile] = File(...)):
    """
    Validate protocol files on clicking of validate button
    """
    try:
        handler = DeploymentEngine(project_id=user_details.project_id)
        data = handler.validate_protocol(user_details=user_details, files=files)
        if "syntax_errors" in data or "errors" in data:
            if "errors" in data and not data["errors"]:
                data.pop("errors")
            if "syntax_errors" in data and not data["syntax_errors"]:
                data.pop("syntax_errors")
            return DefaultFailureResponse(message="Validation Failed", error=data)
        return DefaultResponse(message="Protocol validated successfully", data=data)
    except Exception as e:
        logging.exception(e)
        return DefaultFailureResponse(message="Failed", error=str(e))


@router.get(APIEndPoints.template_download)
def template_download():
    f_path = Path("templates") / "protocol_templates.zip"
    return FileResponse(f_path)
