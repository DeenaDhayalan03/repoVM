import uvicorn
from app import create_app
from scripts.service.todo_service import router as task_router

app = create_app()
app.include_router(task_router, tags=["Task Operations"])

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8002, reload=True)
