import uvicorn
from app import create_app
from scripts.constants.app_configuration import settings

app = create_app(root_path="/app1")

if __name__ == "__main__":
    uvicorn.run(app, host=settings.API_HOST, port=settings.API_PORT)
