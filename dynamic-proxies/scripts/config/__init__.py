from dotenv import load_dotenv
from pydantic_settings import BaseSettings
import tempfile
import pathlib

load_dotenv()


class _EnvConf(BaseSettings):
    env: str = "prod"
    namespace: str = "deenadhayalan"
    image_pull_secret: str = "kl-azregistry"
    host_path: str = "/data2/ut-k8volumes/core-volumes"
    claim_name: str = "core-volumes-pvc"
    kubernetes_log_level: str = "ERROR"


class _Service(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 7212
    workers: int = 4
    TEMP_PATH: pathlib.Path = pathlib.Path("/code/temp")
    TEMP_PATH.mkdir(parents=True, exist_ok=True)
    tempfile.tempdir = TEMP_PATH


class _MongoDB(BaseSettings):
    mongo_uri: str = "mongodb://localhost:27017"


class _IstioGateway(BaseSettings):
    istio_gateway: str = "istio-system/fastapi-gateway"


EnvConf = _EnvConf()
MongoDB = _MongoDB()
IstioGateway = _IstioGateway()
Service = _Service()
