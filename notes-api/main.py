import uvicorn
from app import create_app
from scripts.service.notes_service import router as notes_router

app = create_app()

app.include_router(notes_router, tags=["Notes Operations"])

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=True)

