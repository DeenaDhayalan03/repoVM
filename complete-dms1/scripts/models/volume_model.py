from pydantic import BaseModel
from typing import Optional, Dict, Any


class VolumeCreateRequest(BaseModel):
    name: Optional[str] = None
    driver: Optional[str] = None
    driver_opts: Optional[Dict[str, Any]] = None
    labels: Optional[Dict[str, str]] = None


class VolumeRemoveRequest(BaseModel):
    force: Optional[bool] = False  #
