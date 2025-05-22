class NewQueryBuilder:
    def __init__(self):
        self.pipeline = []

    def project(self, fields):
        self.pipeline.append({"$project": fields})

    def match(self, conditions):
        if conditions:
            self.pipeline.append({"$match": {"$and": conditions}})

    def sort(self, sort_model, key_mapping):
        if sort_model:
            sort_conditions = {
                key_mapping.get(sort["colId"], sort["colId"]): 1 if sort["sort"] == "asc" else -1 for sort in sort_model
            }
            self.pipeline.append({"$sort": sort_conditions})

    def paginate(self, skip, limit):
        self.pipeline.append({"$skip": skip})
        self.pipeline.append({"$limit": limit})

    def build(self):
        return self.pipeline
