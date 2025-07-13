from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class TaskCreateRequest(BaseModel):
    title: str
    description: Optional[str]
    due_date: Optional[datetime]
    priority: Optional[str] = "normal"
    tags: Optional[List[str]] = []

class TaskUpdateRequest(BaseModel):
    title: Optional[str]
    description: Optional[str]
    due_date: Optional[datetime]
    priority: Optional[str]
    tags: Optional[List[str]]
    completed: Optional[bool]

class TaskResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    due_date: Optional[datetime]
    priority: Optional[str]
    completed: bool
    tags: List[str]
    created_at: datetime
    updated_at: datetime

class TaskListResponse(BaseModel):
    tasks: List[TaskResponse]

class AnalyticsResponse(BaseModel):
    total_tasks: int
    completed_tasks: int
    pending_tasks: int
    latest_created_at: Optional[datetime]
