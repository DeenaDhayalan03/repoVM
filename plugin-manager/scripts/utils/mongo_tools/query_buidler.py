import logging

from scripts.constants.schemas import AGGridTableRequest

MG_AGG_REGEX = "$regex"
MG_AGG_PROJECT = "$project"
MG_AGG_OPTIONS = "$options"
MG_AGG_EMPTY = "$empty"
MG_AGG_MATCH = "$match"


class QueryFormationError(Exception):
    """raises when there is an issue in Query formation"""


class AGGridMongoQueryUtil:
    def __init__(self) -> None:
        self.forced_filters = {}
        self.filter_query = []
        self.sort_query = {}
        self.value_col_filter = {}
        self.aggregation_pipeline = []
        self.skip = {}
        self.limit = {}

    def build_query(self, req_body: AGGridTableRequest, *, additional_projection: dict | None = None) -> list[dict]:
        try:
            filters = req_body.filters
            start_row = req_body.start_row
            end_row = req_body.end_row

            if start_row > 0:
                self.skip = {"$skip": start_row}

            limit = end_row - start_row
            self.limit = {"$limit": limit}

            if filters:
                self.form_filter_query(
                    sort_model=filters.sort_model, filter_model=filters.filter_model, value_cols=filters.value_cols
                )

            stages = (
                self.forced_filters,
                self.filter_query,
                self.sort_query,
                self.skip,
                self.limit,
                self.value_col_filter,
            )

            for stage in stages:
                if stage:
                    if isinstance(stage, list):
                        self.aggregation_pipeline.extend(stage)
                    else:
                        self.aggregation_pipeline.append(stage)

            if additional_projection:
                self.aggregation_pipeline.append({MG_AGG_PROJECT: additional_projection})
            return self.aggregation_pipeline
        except Exception as e:
            logging.exception(e)
            raise QueryFormationError from e

    def form_filter_query(self, sort_model: list, filter_model: dict, value_cols: list) -> None:
        is_filtering = len(filter_model) > 0
        if is_filtering:
            for column, filter_obj in filter_model.items():
                query = self.build_column_query(filter_obj, column)
                self.filter_query.append(query)

        is_sorting = len(sort_model) > 0

        if is_sorting:
            self.form_sort_query(sort_model=sort_model)

        if value_cols:
            self.value_col_filter = {MG_AGG_PROJECT: {"_id": 0} | {col: 1 for col in value_cols}}

    def form_sort_query(self, sort_model: list) -> None:
        _sort = {}
        for sort_obj in sort_model:
            order = 1 if sort_obj["sort"] == "asc" else -1
            _sort[sort_obj["colId"]] = order
        self.sort_query = {"$sort": _sort}

    @staticmethod
    def build_text_query(filter_obj, column) -> dict:
        try:
            filter_value = filter_obj["filter"]
            # Check if the column is 'version' and convert the filter value to float
            if column == "version":
                try:
                    filter_value = float(filter_value)
                except ValueError:
                    raise ValueError(f"Invalid filter value for version: {filter_value}")

            query_map = {
                "contains": (
                    {column: {MG_AGG_REGEX: filter_value, MG_AGG_OPTIONS: "i"}}
                    if isinstance(filter_value, str)
                    else {column: filter_value}
                ),
                "equals": {column: filter_value},
                "notEqual": {column: {"$ne": filter_value}},
                "notContains": (
                    {column: {"$not": {MG_AGG_REGEX: filter_value, MG_AGG_OPTIONS: "i"}}}
                    if isinstance(filter_value, str)
                    else {column: {"$ne": filter_value}}
                ),
                "startsWith": (
                    {column: {MG_AGG_REGEX: "^" + filter_value, MG_AGG_OPTIONS: "i"}}
                    if isinstance(filter_value, str)
                    else {column: filter_value}
                ),
                "endsWith": (
                    {column: {MG_AGG_REGEX: filter_value + "$", MG_AGG_OPTIONS: "i"}}
                    if isinstance(filter_value, str)
                    else {column: filter_value}
                ),
                "blank": {"$or": [{column: {MG_AGG_EMPTY: True, "$eq": ""}}, {column: {MG_AGG_EMPTY: False}}]},
                "notBlank": {column: {"$exists": True, "$ne": ""}},
                "false": {column: False},
                "true": {column: True},
            }
            return query_map[filter_obj["type"]]
        except KeyError:
            raise NotImplementedError(f'given text search is not supported: {filter_obj["type"]}')

    @staticmethod
    def build_number_query(filter_obj, column) -> dict:
        try:
            query_map = {
                "equals": {column: filter_obj["filter"]},
                "notEqual": {column: {"$ne": filter_obj["filter"]}},
                "lessThan": {column: {"$lt": filter_obj["filter"]}},
                "lessThanOrEqual": {column: {"$lte": filter_obj["filter"]}},
                "greaterThan": {column: {"$gt": filter_obj["filter"]}},
                "greaterThanOrEqual": {column: {"$gte": filter_obj["filter"]}},
                "inRange": {column: {"$and": [{"$lt": filter_obj["filterTo"]}, {"$gt": filter_obj["filter"]}]}},
                "blank": {"$or": [{column: {MG_AGG_EMPTY: True, "$eq": ""}}, {column: {MG_AGG_EMPTY: False}}]},
                "notBlank": {column: {"$exists": True, "$ne": ""}},
                "false": {column: False},
                "true": {column: True},
            }
            return query_map[filter_obj["type"]]
        except KeyError:
            raise NotImplementedError(f'given text search is not supported: {filter_obj["type"]}')

    def build_date_query(self, filter_obj, column) -> dict:
        return self.build_number_query(filter_obj, column)

    def simple_search_query(self, filter_obj, column) -> dict:
        func_map = {"text": self.build_text_query, "number": self.build_number_query, "date": self.build_date_query}
        filter_type = filter_obj.get("filterType", "undef")
        func = func_map.get(filter_type)
        if not func:
            raise QueryFormationError
        return func(filter_obj, column)

    def value_search_query(self, filter_obj, column) -> dict:
        return {column: {"$in": filter_obj["values"]}}

    def build_column_query(self, filter_obj, column) -> dict:
        if "operator" in filter_obj:
            query = {MG_AGG_MATCH: self.handle_operator_filter(filter_obj, column)}
        elif "values" in filter_obj:
            query = self.value_search_query(filter_obj, column)
        elif "filterType" in filter_obj:
            if filter_obj["filterType"] == "set":
                query = self.handle_set_filter(filter_obj, column)
            else:
                query = self.simple_search_query(filter_obj, column)
        else:
            raise ValueError("Invalid filter type: " + filter_obj["filterType"])
        return {MG_AGG_MATCH: query}

    @staticmethod
    def handle_operator_filter(filter_obj, column) -> dict:
        operator = filter_obj["operator"]
        condition1 = filter_obj["condition1"]
        condition2 = filter_obj["condition2"]

        if operator == "AND":
            return {"$and": [{column: condition1}, {column: condition2}]}
        elif operator == "OR":
            return {"$or": [{column: condition1}, {column: condition2}]}
        else:
            raise ValueError("Invalid operator: " + operator)

    @staticmethod
    def handle_set_filter(filter_obj, column) -> dict:
        """
        /* UI should send object similar to the below :
        "filterModel" :
        {
            "country": {
                "values": [
                    "Afghanistan",
                    "Algeria"
                ],
                "filterType": "set"
            },
            "sport": {
                "values": [
                    "Athletics",
                    "Taekwondo"
                ],
                "filterType": "set"
            }
        }
         */
        """
        return {MG_AGG_MATCH: {column: {"$in": filter_obj["values"]}}}
