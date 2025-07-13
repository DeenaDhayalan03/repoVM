from fastapi import FastAPI

def create_app() -> FastAPI:
    app = FastAPI(title="Standalone Notes API")
    return app
