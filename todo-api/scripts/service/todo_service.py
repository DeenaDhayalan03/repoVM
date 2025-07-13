from fastapi import APIRouter, HTTPException
from constants.api import TaskAPIEndpoints
from scripts.handler import todo_handler
from scripts.model.todo_model import (
    TaskCreateRequest,
    TaskUpdateRequest,
    TaskResponse,
    TaskListResponse,
    AnalyticsResponse,
)

router = APIRouter()

@router.get(TaskAPIEndpoints.ANALYTICS, response_model=AnalyticsResponse)
async def get_analytics():
    return todo_handler.get_analytics()

@router.post(TaskAPIEndpoints.CREATE_TASK)
async def create_task(payload: TaskCreateRequest):
    result = todo_handler.create_task(payload.dict())
    return {"message": "Task created", "task_id": str(result.inserted_id)}

@router.get(TaskAPIEndpoints.LIST_TASKS, response_model=TaskListResponse)
async def list_tasks(limit: int = 10, offset: int = 0):
    tasks = todo_handler.list_tasks(limit, offset)
    return {
        "tasks": [
            TaskResponse(
                id=str(task["_id"]),
                title=task["title"],
                description=task.get("description"),
                due_date=task.get("due_date"),
                priority=task.get("priority", "normal"),
                completed=task.get("completed", False),
                tags=task.get("tags", []),
                created_at=task["created_at"],
                updated_at=task["updated_at"]
            ) for task in tasks
        ]
    }

@router.get(TaskAPIEndpoints.GET_TASK, response_model=TaskResponse)
async def get_task(task_id: str):
    task = todo_handler.get_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse(
        id=str(task["_id"]),
        title=task["title"],
        description=task.get("description"),
        due_date=task.get("due_date"),
        priority=task.get("priority", "normal"),
        completed=task.get("completed", False),
        tags=task.get("tags", []),
        created_at=task["created_at"],
        updated_at=task["updated_at"]
    )

@router.patch(TaskAPIEndpoints.UPDATE_TASK)
async def update_task(task_id: str, payload: TaskUpdateRequest):
    result = todo_handler.update_task(task_id, payload.dict(exclude_unset=True))
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Task not found or nothing to update")
    return {"message": "Task updated"}

@router.delete(TaskAPIEndpoints.DELETE_TASK)
async def delete_task(task_id: str):
    result = todo_handler.delete_task(task_id)
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task deleted"}


