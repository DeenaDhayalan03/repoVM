from datetime import datetime
from bson import ObjectId
from scripts.utils.mongo_util import get_tasks_collection

def create_task(task: dict):
    task["created_at"] = datetime.utcnow()
    task["updated_at"] = datetime.utcnow()
    task["completed"] = False
    return get_tasks_collection().insert_one(task)

def list_tasks(limit: int = 10, offset: int = 0):
    return list(get_tasks_collection().find().skip(offset).limit(limit))

def get_task_by_id(task_id: str):
    return get_tasks_collection().find_one({"_id": ObjectId(task_id)})

def update_task(task_id: str, update_data: dict):
    update_data["updated_at"] = datetime.utcnow()
    return get_tasks_collection().update_one(
        {"_id": ObjectId(task_id)}, {"$set": update_data}
    )

def delete_task(task_id: str):
    return get_tasks_collection().delete_one({"_id": ObjectId(task_id)})

def get_analytics():
    col = get_tasks_collection()
    total = col.count_documents({})
    completed = col.count_documents({"completed": True})
    pending = total - completed
    last = col.find().sort("created_at", -1).limit(1)
    return {
        "total_tasks": total,
        "completed_tasks": completed,
        "pending_tasks": pending,
        "latest_created_at": next(last, {}).get("created_at")
    }
