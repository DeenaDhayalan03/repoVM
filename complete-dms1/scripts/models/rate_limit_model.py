from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class RateLimitConfig(BaseModel):
    user_id: str
    limit: int
    time_window: int
    reset_time: Optional[datetime] = None
    remaining: int = 0
    last_reset: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
