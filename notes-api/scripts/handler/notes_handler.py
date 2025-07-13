from scripts.utils.mongo_utils import get_notes_collection
from datetime import datetime
from bson import ObjectId


def create_note(note_data: dict):
    note_data["created_at"] = datetime.utcnow()
    note_data["updated_at"] = datetime.utcnow()
    return get_notes_collection().insert_one(note_data)


def get_note_by_id(note_id: str):
    return get_notes_collection().find_one({"_id": ObjectId(note_id)})


def list_notes(limit: int = 10, offset: int = 0):
    return list(get_notes_collection().find().skip(offset).limit(limit))


def update_note(note_id: str, update_data: dict):
    update_data["updated_at"] = datetime.utcnow()
    return get_notes_collection().update_one({"_id": ObjectId(note_id)}, {"$set": update_data})


def delete_note(note_id: str):
    return get_notes_collection().delete_one({"_id": ObjectId(note_id)})


def get_note_analytics():
    total = get_notes_collection().count_documents({})
    last_note = get_notes_collection().find().sort("created_at", -1).limit(1)
    latest = next(last_note, None)
    return {
        "total_notes": total,
        "latest_created_at": latest["created_at"] if latest else None
    }
