from pymongo import MongoClient
from constants.app_configuration import config

def get_mongo_client():
    return MongoClient(config.MONGO_URI)

def get_notes_collection():
    client = get_mongo_client()
    db = client[config.MONGO_DB_NAME]
    return db[config.MONGO_COLLECTION_NAME]
