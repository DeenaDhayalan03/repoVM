from scripts.config import MongoDB
from scripts.utils.mongo_util import MongoConnect

mongo_client = MongoConnect(uri=MongoDB.mongo_uri)()
