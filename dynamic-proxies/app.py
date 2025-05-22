import uvicorn

from scripts.config import Service

if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    uvicorn.run("main:app", host=Service.host, port=Service.port, workers=Service.workers)
