from pymongo import MongoClient
from constants.app_configuration import config

def get_mongo_db():
    client = MongoClient(config.MONGODB_URI)
    return client[config.MONGODB_DB]
