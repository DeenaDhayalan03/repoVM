from fastapi import APIRouter, Form, UploadFile, File
from typing import Annotated
import json
from constants.api import Endpoints
from scripts.handler.postgres_handler import handle_postgres_bulk_upload_auto_infer, fetch_upi_data_postgres

router = APIRouter()

@router.post(Endpoints.READ_TRANSACTIONS)
async def read_upi_transactions(
    search: Annotated[str, Form()]
):
    try:
        search_dict = json.loads(search)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON format in 'search' field."}

    return fetch_upi_data_postgres(search_dict)

@router.post(Endpoints.BULK_UPLOAD)
async def bulk_upload_postgres(
    table_name: str = Form(...),
    file: UploadFile = File(...)
):
    return handle_postgres_bulk_upload_auto_infer(table_name, file)
