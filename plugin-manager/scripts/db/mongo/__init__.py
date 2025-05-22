from pydantic import BaseModel

from scripts.config import Databases
from scripts.utils.mongo_util import MongoConnect

mongo_obj = MongoConnect(uri=Databases.MONGO_URI)

mongo_client = mongo_obj()

CollectionBaseClass = mongo_obj.get_base_class()


class MongoBaseSchema(BaseModel):
    pass
