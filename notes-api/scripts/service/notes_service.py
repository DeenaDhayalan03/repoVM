from fastapi import APIRouter, HTTPException
from constants.api import NotesAPIEndpoints
from scripts.handler import notes_handler
from scripts.models.notes_model import (
    NoteCreateRequest,
    NoteUpdateRequest,
    NoteResponse,
    NotesListResponse,
    AnalyticsResponse,
)
from bson import ObjectId

router = APIRouter()

@router.get(NotesAPIEndpoints.ANALYTICS, response_model=AnalyticsResponse)
async def get_analytics():
    return notes_handler.get_note_analytics()

@router.get(NotesAPIEndpoints.LIST_NOTES, response_model=NotesListResponse)
async def list_notes(limit: int = 10, offset: int = 0):
    notes = notes_handler.list_notes(limit, offset)
    formatted = []
    for note in notes:
        formatted.append(
            NoteResponse(
                id=str(note["_id"]),
                title=note["title"],
                content=note["content"],
                tags=note.get("tags", []),
                created_at=note["created_at"],
                updated_at=note["updated_at"],
            )
        )
    return {"notes": formatted}


@router.post(NotesAPIEndpoints.CREATE_NOTE)
async def create_note(payload: NoteCreateRequest):
    result = notes_handler.create_note(payload.dict())
    return {"message": "Note created", "note_id": str(result.inserted_id)}


@router.get(NotesAPIEndpoints.GET_NOTE, response_model=NoteResponse)
async def get_note(note_id: str):
    note = notes_handler.get_note_by_id(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return NoteResponse(
        id=str(note["_id"]),
        title=note["title"],
        content=note["content"],
        tags=note.get("tags", []),
        created_at=note["created_at"],
        updated_at=note["updated_at"],
    )


@router.patch(NotesAPIEndpoints.UPDATE_NOTE)
async def update_note(note_id: str, payload: NoteUpdateRequest):
    result = notes_handler.update_note(note_id, payload.dict(exclude_unset=True))
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Note not found or nothing to update")
    return {"message": "Note updated"}


@router.delete(NotesAPIEndpoints.DELETE_NOTE)
async def delete_note(note_id: str):
    result = notes_handler.delete_note(note_id)
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"message": "Note deleted"}

