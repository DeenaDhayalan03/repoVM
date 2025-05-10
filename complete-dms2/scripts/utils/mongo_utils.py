from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from scripts.constants.app_configuration import settings
from scripts.logging.logger import logger

class MongoDBConnection:
    def __init__(self):
        try:
            self.client = MongoClient(settings.MONGODB_URL, tls=True)
            self.db = self.client[settings.MONGODB_DATABASE]
            self.client.admin.command('ping')
            logger.info("Connected successfully to MongoDB Atlas.")
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB Atlas: {e}")
            raise

    def get_collection(self, collection_name: str):
        return self.db[collection_name]
