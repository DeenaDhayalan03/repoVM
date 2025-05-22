from ut_mongo_util import CollectionBaseClass, mongo_client


class UserCollectionKeys:
    KEY_LANGUAGE = "language"
    KEY_NAME = "name"
    KEY_USER_ID = "user_id"
    KEY_SPACE_ID = "space_id"
    KEY_USERNAME = "username"
    KEY_USER_ROLE = "userrole"


class UserSpace(CollectionBaseClass):
    key_username = UserCollectionKeys.KEY_USERNAME
    key_user_id = UserCollectionKeys.KEY_USER_ID
    key_language = UserCollectionKeys.KEY_LANGUAGE
    key_name = UserCollectionKeys.KEY_NAME
    key_space_id = UserCollectionKeys.KEY_SPACE_ID

    def __init__(self):
        super().__init__(
            mongo_client,
            database="catalog_meta",
            collection="user_space",
        )

    def fetch_user_space(self, user_id, space_id):
        query = {self.key_user_id: user_id, self.key_space_id: space_id}
        user = self.find_one(query=query)
        return user

    def fetch_user_space_with_details(self, user_id, space_id):
        query = [
            {"$match": {"user_id": user_id, "space_id": space_id}},
            {"$lookup": {"from": "user", "localField": "user_id", "foreignField": "user_id", "as": "user_details"}},
            {"$unwind": {"path": "$user_details"}},
            {
                "$project": {
                    "space_id": 1,
                    "AccessLevel": 1,
                    "access_group_ids": 1,
                    "userrole": 1,
                    "user_id": 1,
                    "name": "$user_details.name",
                    "email": "$user_details.email",
                    "username": "$user_details.username",
                }
            },
        ]
        user = self.aggregate(query)
        user_list = list(user)
        if user_list:
            return user_list[0]
        else:
            return None

    def find_user_role_for_user_id(self, user_id, space_id):
        query = {"user_id": user_id, "space_id": space_id}
        filter_dict = {"userrole": 1, "_id": 0}
        return self.find_one(query=query, filter_dict=filter_dict)

    def update_one_user_space(self, data, user_id, space_id):
        query = {self.key_user_id: user_id, "space_id": space_id}
        return self.update_one(query=query, data=data, upsert=True)

    def insert_one_user(self, data):
        """
        The following function will insert one user in the
        user collections
        :param self:
        :param data:
        :return:
        """
        return self.insert_one(data)

    def delete_one_user_space(self, user_id, space_id):
        return self.delete_one(query={self.key_user_id: user_id, self.key_space_id: space_id})

    def list_spaces(self, user_id):
        query = {self.key_user_id: user_id}
        return self.distinct(query_key=self.key_space_id, filter_json=query)
