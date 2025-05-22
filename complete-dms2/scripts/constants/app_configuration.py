from pydantic_settings import BaseSettings

class Settings(BaseSettings):

    API_HOST: str
    API_PORT: int

    DOCKER_SOCK: str
    DOCKER_CLIENT_TIMEOUT: int

    MONGODB_URL: str
    MONGODB_DATABASE: str

    JWT_SECRET: str
    JWT_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    DEFAULT_DOCKER_TAG: str = "default:latest"
    DEFAULT_MAX_CONTAINERS_PER_HOUR: int


    class Config:
        env_file = ".env"

settings = Settings()
