from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API Config
    API_HOST: str
    API_PORT: int

    # Docker
    DOCKER_SOCK: str
    DOCKER_CLIENT_TIMEOUT: int

    # MongoDB
    MONGODB_URL: str
    MONGODB_DATABASE: str

    # Auth
    JWT_SECRET: str
    JWT_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    # Docker image build
    DEFAULT_DOCKER_TAG: str = "default:latest"
    DEFAULT_MAX_CONTAINERS_PER_HOUR: int

    # Kubernetes / Kaniko
    KANIKO_IMAGE: str
    KANIKO_NAMESPACE: str
    DOCKER_SECRET_NAME: str
    KUBECONFIG: str

    class Config:
        env_file = ".env"

settings = Settings()
