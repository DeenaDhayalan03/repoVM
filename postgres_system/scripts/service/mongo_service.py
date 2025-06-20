from fastapi import APIRouter, UploadFile, File, Form
from typing import Annotated
import json
from scripts.handler.mongo_handler import fetch_upi_data_mongo, handle_mongo_upload
from constants.api import Endpoints

router = APIRouter()

@router.post(Endpoints.READ_TRANSACTIONS_MONGO)
async def read_upi_transactions_mongo(
    search: Annotated[str, Form()]
):
    try:
        search_dict = json.loads(search)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON format in 'search' field."}

    return fetch_upi_data_mongo(search_dict)

@router.post(Endpoints.BULK_UPLOAD_MONGO)
async def upload_to_mongo(
    index_type: str = Form(...),
    file: UploadFile = File(...)
):
    return handle_mongo_upload(index_type, file)