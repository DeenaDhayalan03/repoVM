import uvicorn
from app import create_app
from scripts.service.postgres_service import router as postgres_router
from scripts.service.mongo_service import router as mongo_router


app = create_app()

app.include_router(postgres_router, tags=["Postgres Operations"])
app.include_router(mongo_router, tags=["Mongo Operations"])

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
