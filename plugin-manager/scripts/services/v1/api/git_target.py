import logging
from fastapi import APIRouter, HTTPException, Depends
from scripts.services.v1.schemas import (
    GitTargetCreateUpdateSchema,
    DefaultFailureResponse,
    DefaultResponse,
    DeleteGitTargets,
    GitTargetListRequest,
)
from scripts.services.v1.handler.git_target import GitTargetHandler
from scripts.constants import GitApiEndPoints
from ut_security_util import MetaInfoSchema
from scripts.utils.rbac import RBAC

router = APIRouter(prefix=GitApiEndPoints.git_services_base, tags=["v1 | Git Target APIs"])


@router.post(
    GitApiEndPoints.git_target_create,
    dependencies=[Depends(RBAC(entity_name="git", operation=["create", "edit", "view"]))],
)
def save_git_target(
    data: GitTargetCreateUpdateSchema,
    user_details: MetaInfoSchema,
):
    """
    The save_git_target function is used to create or update a git target.
    """
    target_id = data.git_target_id if hasattr(data, "git_target_id") else None
    handler = GitTargetHandler(project_id=user_details.project_id)
    try:
        response = handler.save_git_target(target_id, data, user_details)
        if isinstance(response, DefaultFailureResponse):
            return DefaultFailureResponse(message="Failed to save git target", error=response.message)
        return DefaultResponse(message="Git target saved successfully", data=response)
    except Exception as e:
        logging.exception(e)
        return DefaultFailureResponse(message="Failed to save git target", error=str(e))


@router.post(GitApiEndPoints.git_target_list, dependencies=[Depends(RBAC(entity_name="git", operation=["view"]))])
def list_git_targets(user_details: MetaInfoSchema, list_request: GitTargetListRequest):
    """
    The list_git_targets function is used to list all the Git targets in a project.
    """
    handler = GitTargetHandler(project_id=user_details.project_id)
    try:
        if list_request.portal:
            response = handler.list_portal_git_targets(list_request)
        else:
            response = handler.list_git_targets(list_request)
        return DefaultResponse(
            message="success",
            data=response,
        )
    except Exception as e:
        logging.exception(e)
        raise HTTPException(
            status_code=500,
            detail="Failed to list Git targets",
        )


@router.get(GitApiEndPoints.git_target_get, dependencies=[Depends(RBAC(entity_name="git", operation=["view"]))])
def get_git_target(git_target_id: str, user_details: MetaInfoSchema):
    """
    The get_git_target function retrieves information about a specific Git target by its ID.
    """
    handler = GitTargetHandler(project_id=user_details.project_id)
    try:
        response = handler.get_git_target(git_target_id)
        if isinstance(response, DefaultFailureResponse):
            return DefaultFailureResponse(message="Failed to retrieve git target", error=response.message)
        return DefaultResponse(message="Git target retrieved successfully", data=response)
    except Exception as e:
        logging.exception(e)
        return DefaultFailureResponse(
            status_code=500,
            message="Failed to retrieve Git target",
        )


@router.delete(GitApiEndPoints.git_target_delete, dependencies=[Depends(RBAC(entity_name="git", operation=["delete"]))])
def delete_git_targets(user_details: MetaInfoSchema, request_data: DeleteGitTargets):
    """The delete_git_targets function deletes multiple git targets."""
    handler = GitTargetHandler(project_id=user_details.project_id)
    results = []
    target_ids = request_data.target_ids if isinstance(request_data.target_ids, list) else [request_data.target_ids]

    try:
        for target_id in target_ids:
            response = handler.delete_git_target(target_id)
            if isinstance(response, DefaultFailureResponse):
                results.append(DefaultResponse(message="Failed to delete git target", data=response))
            else:
                results.append(response)
        return DefaultResponse(message="Git targets deleted successfully", data=results)
    except HTTPException as e:
        if (
            e.detail
            == "This Git target cannot be deleted because it is associated with existing plugins. Please delete all related plugins before attempting to delete this Git target."
        ):
            return DefaultFailureResponse(
                message="This Git target cannot be deleted because it is associated with existing plugins. Please delete all related plugins before attempting to delete this Git target.",
                error=str(e.detail),
            )
        logging.exception(e)
        return DefaultFailureResponse(message="Failed to delete git targets", error=str(e))


@router.post(GitApiEndPoints.git_validation, dependencies=[Depends(RBAC(entity_name="git", operation=["view"]))])
def git_validation(data: GitTargetCreateUpdateSchema):
    """
    The git_validation function is used to validate git credentials.
    """
    try:
        handler = GitTargetHandler()
        if handler.git_validation(data):
            return DefaultResponse(message="The credentials have been verified and authenticated", data={})
        else:
            return DefaultFailureResponse(
                message="Authentication failed. Please verify your credentials and try again",
                error={"error": "Invalid credentials"},
            )

    except Exception as e:
        logging.exception(e)
        return DefaultFailureResponse(
            message="Authentication failed. Please verify your credentials and try again", error=str(e)
        )


@router.get(
    GitApiEndPoints.git_headercontent,
    include_in_schema=False,
    dependencies=[Depends(RBAC(entity_name="git", operation=["view"]))],
)
def get_git_pluginheadercontent(user_details: MetaInfoSchema):
    try:
        git_handler = GitTargetHandler(project_id=user_details.project_id)
        header_content = git_handler.git_headercontent()
        return {"status": "success", "message": "success", "data": header_content}
    except Exception as e:
        return {"status": "failed", "message": "Failed", "error": str(e)}
