from pydantic_settings import BaseSettings

class AppConfig(BaseSettings):
    DATABASE_URL: str
    MONGODB_URI: str
    MONGODB_DB: str
    MONGODB_COLLECTION_UNINDEXED: str
    MONGODB_COLLECTION_INDEXED: str
    UPSTASH_REDIS_REST_URL: str

    class Config:
        env_file = ".env"

config = AppConfig()
