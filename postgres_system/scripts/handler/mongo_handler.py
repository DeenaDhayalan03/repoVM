from scripts.utils.mongo_utils import get_mongo_db
from scripts.utils.redis_utils import get_cache, set_cache
from constants.app_configuration import config
from constants.app_constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE
from fastapi import UploadFile
import json
import csv
import io
import hashlib

def serialize_doc(doc):
    doc["_id"] = str(doc["_id"])
    return doc

def handle_mongo_upload(collection_name: str, file: UploadFile) -> dict:
    try:
        db = get_mongo_db()
        collection = db[collection_name]

        filename = file.filename.lower()
        content = file.file.read()

        if filename.endswith(".csv"):
            decoded = content.decode("utf-8")
            reader = csv.DictReader(io.StringIO(decoded))
            documents = [dict(row) for row in reader]

        elif filename.endswith(".json"):
            decoded = content.decode("utf-8")
            data = json.loads(decoded)
            documents = data if isinstance(data, list) else [data]

        else:
            return {"error": "Unsupported file type. Use .csv or .json"}

        if not documents:
            return {"error": "No valid documents to insert."}

        result = collection.insert_many(documents)
        return {"inserted_count": len(result.inserted_ids)}

    except Exception as e:
        return {"error": str(e)}

def fetch_upi_data_mongo(search: dict):
    filters = search.get("filter", {})
    pagination = search.get("pagination", {})
    sorting = search.get("sort", [])
    query_text = search.get("query", "")
    index_type = search.get("index_type", "indexed")
    suggest = search.get("suggest", False)

    try:
        cache_key_raw = json.dumps(search, sort_keys=True)
        cache_key = "upi_mongo_cache:" + hashlib.sha256(cache_key_raw.encode()).hexdigest()

        cached_result = get_cache(cache_key)
        if cached_result:
            return cached_result

        db = get_mongo_db()
        if index_type == "indexed":
            collection_name = config.MONGODB_COLLECTION_INDEXED
        else:
            collection_name = config.MONGODB_COLLECTION_UNINDEXED
        collection = db[collection_name]

        if suggest and query_text:
            suggestion_fields = ["sender_bank", "sender_state", "transaction_status"]
            suggestions = []

            for field in suggestion_fields:
                pipeline = [
                    {
                        "$search": {
                            "index": "default",
                            "autocomplete": {
                                "query": query_text,
                                "path": field,
                                "fuzzy": { "maxEdits": 1 }
                            }
                        }
                    },
                    {"$limit": 5},
                    {"$project": { "_id": 0, field: 1 }}
                ]
                results = list(collection.aggregate(pipeline))
                suggestions.extend(results)

            unique_suggestions = {}
            for item in suggestions:
                for field, value in item.items():
                    if field not in unique_suggestions:
                        unique_suggestions[field] = set()
                    unique_suggestions[field].add(value)

            flat_suggestions = {
                field: list(values) for field, values in unique_suggestions.items()
            }

            set_cache(cache_key, {"suggestions": flat_suggestions})
            return {"suggestions": flat_suggestions}

        query = {}
        if filters.get("sender_state"):
            query["sender_state"] = filters["sender_state"]
        if filters.get("transaction_status"):
            query["transaction_status"] = filters["transaction_status"]
        if filters.get("sender_bank"):
            query["sender_bank"] = filters["sender_bank"]

        amount_range = {}
        if filters.get("min_amount") is not None:
            amount_range["$gte"] = filters["min_amount"]
        if filters.get("max_amount") is not None:
            amount_range["$lte"] = filters["max_amount"]
        if amount_range:
            query["amount_inr"] = amount_range

        pipeline = []

        if query_text:
            pipeline.append({
                "$search": {
                    "index": "default",
                    "text": {
                        "query": query_text,
                        "path": ["sender_bank", "sender_state", "transaction_status"]
                    }
                }
            })

        if query:
            pipeline.append({ "$match": query })

        sort_fields = {}
        for rule in sorting:
            field = rule.get("field")
            order = rule.get("order", "asc")
            if field:
                sort_fields[field] = 1 if order == "asc" else -1
        if sort_fields:
            pipeline.append({ "$sort": sort_fields })

        limit = pagination.get("page_size", DEFAULT_PAGE_SIZE)
        page = pagination.get("page", DEFAULT_PAGE)
        skip = (page - 1) * limit

        pipeline.extend([
            { "$skip": skip },
            { "$limit": limit }
        ])

        results = list(collection.aggregate(pipeline))
        count = collection.count_documents(query)

        final_result = {
            "data": [serialize_doc(doc) for doc in results],
            "count": count,
            "page": page,
            "page_size": limit
        }

        set_cache(cache_key, final_result)
        return final_result

    except Exception as e:
        return { "error": str(e) }
