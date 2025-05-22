import logging
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends
from fastapi.responses import Response
from ut_security_util import MetaInfoSchema
from scripts.utils.rbac import RBAC

from scripts.constants import APIEndPoints
from scripts.services.v1.handler import UIServiceHandler
from scripts.services.v1.schemas import (
    DefaultFailureResponse,
    DefaultResponse,
    UIDropdowns,
)

router = APIRouter(prefix=APIEndPoints.ui_services_base, tags=["v1 | UI Services"])


@router.post(
    APIEndPoints.get_dropdown_elements, dependencies=[Depends(RBAC(entity_name="developerPlugins", operation=["view"]))]
)
def get_dropdowns(user_details: MetaInfoSchema, req: UIDropdowns):
    try:
        handler = UIServiceHandler(user_details.project_id)
        data = handler.get_dropdowns(elements=req.elements, portal=req.portal)
        return DefaultResponse(message="Dropdowns fetched successfully", data=data)
    except Exception as e:
        logging.exception(e)
        return DefaultFailureResponse(message="Failed", error=str(e))


@router.get(
    APIEndPoints.get_dropdown_elements, dependencies=[Depends(RBAC(entity_name="developerPlugins", operation=["view"]))]
)
def get_dropdown(user_details: MetaInfoSchema, element: str):
    try:
        handler = UIServiceHandler(user_details.project_id)
        data = handler.get_dropdowns(elements=[element])
        return DefaultResponse(message="Dropdowns fetched successfully", data=data)
    except Exception as e:
        logging.exception(e)
        return DefaultFailureResponse(message="Failed", error=str(e))


@router.post(
    APIEndPoints.update_dropdown_elements,
    dependencies=[Depends(RBAC(entity_name="developerPlugins", operation=["edit"]))],
    include_in_schema=False,
)
def update_dropdown(user_details: MetaInfoSchema, content_type: str, data: Annotated[Any, Body()]):
    try:
        handler = UIServiceHandler(user_details.project_id)
        handler.update_constants(content_type=content_type, data=data)
        return Response(status_code=201)
    except Exception as e:
        logging.exception(e)
        return DefaultFailureResponse(message="Failed", error=str(e))


@router.get(
    APIEndPoints.get_dependant_dropdown_elements,
    dependencies=[Depends(RBAC(entity_name="developerPlugins", operation=["view"]))],
)
def get_dependant_dropdown(user_details: MetaInfoSchema, parent: str, portal: bool = False):
    try:
        handler = UIServiceHandler(user_details.project_id)
        data = handler.get_dependant_dropdown_plugin(parent=parent, portal=portal)
        return DefaultResponse(message="Dropdown fetched successfully", data=data)
    except Exception as e:
        logging.exception(e)
        return DefaultFailureResponse(message="Failed", error=str(e))
