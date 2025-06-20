import redis
import json
from constants.app_configuration import config

redis_client = redis.Redis.from_url(config.UPSTASH_REDIS_REST_URL, decode_responses=True)

def get_cache(key: str):
    cached = redis_client.get(key)
    return json.loads(cached) if cached else None

def set_cache(key: str, value: dict, ttl: int = 3600):
    redis_client.setex(key, ttl, json.dumps(value))
