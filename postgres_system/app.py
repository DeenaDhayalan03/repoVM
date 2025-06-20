from fastapi import FastAPI

def create_app() -> FastAPI:
    app = FastAPI(title="UPI Transaction API")
    return app
