from pydantic_settings import BaseSettings

class AppConfig(BaseSettings):
    MONGO_URI: str
    MONGO_DB_NAME: str
    MONGO_COLLECTION_NAME: str

    class Config:
        env_file = ".env"

config = AppConfig()
