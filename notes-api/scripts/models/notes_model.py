from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class NoteCreateRequest(BaseModel):
    title: str
    content: str
    tags: Optional[List[str]] = []

class NoteUpdateRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None

class NoteResponse(BaseModel):
    id: str
    title: str
    content: str
    tags: Optional[List[str]]
    created_at: datetime
    updated_at: datetime

class NotesListResponse(BaseModel):
    notes: List[NoteResponse]

class AnalyticsResponse(BaseModel):
    total_notes: int
    latest_created_at: Optional[datetime]
