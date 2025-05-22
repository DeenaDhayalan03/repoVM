from ut_redis_connector import RedisConnector

from scripts.config import Databases

connector = RedisConnector(redis_uri=Databases.REDIS_URI)
login_db = connector.connect(db=int(Databases.REDIS_LOGIN_DB), decode_responses=True)
user_role_permissions_redis = connector.connect(db=int(Databases.REDIS_USER_ROLE_DB), decode_responses=True)
project_details_db = connector.connect(db=int(Databases.REDIS_PROJECT_DB), decode_responses=True)
