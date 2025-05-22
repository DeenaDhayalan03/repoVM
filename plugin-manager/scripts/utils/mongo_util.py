"""Mongo DB utility
All definitions related to mongo db is defined in this module
"""

import logging

from pymongo import MongoClient

from .mongo_tools import mongo_sync


class MongoConnect:
    def __init__(self, uri):
        try:
            self.uri = uri
            self.client = MongoClient(uri, connect=False)
        except Exception as e:
            logging.exception(e)
            raise

    def __call__(self, *args, **kwargs):
        return self.client

    def get_client(self):
        return self.client

    def __repr__(self):
        return f"Mongo Client(uri:{self.uri}, server_info={self.client.server_info()})"

    @staticmethod
    def get_base_class():
        return mongo_sync.MongoCollectionBaseClass


class MongoStageCreator:
    @staticmethod
    def add_stage(stage_name: str, stage: dict) -> dict:
        return {stage_name: stage}

    def projection_stage(self, stage: dict) -> dict:
        return self.add_stage("$project", stage)

    def match_stage(self, stage: dict) -> dict:
        return self.add_stage("$match", stage)

    def lookup_stage(self, stage: dict) -> dict:
        return self.add_stage("$lookup", stage)

    def unwind_stage(self, stage: dict) -> dict:
        return self.add_stage("$unwind", stage)

    def group_stage(self, stage: dict) -> dict:
        return self.add_stage("$group", stage)

    def add_fields(self, stage: dict) -> dict:
        return self.add_stage("$addFields", stage)

    def sort_stage(self, stage: dict) -> dict:
        return self.add_stage("$sort", stage)
