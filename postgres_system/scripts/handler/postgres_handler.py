import hashlib
import json
import csv
import io
import re
from decimal import Decimal
from datetime import datetime
from fastapi import UploadFile
from scripts.utils.postgres_utils import get_postgres_connection
from scripts.utils.redis_utils import get_cache, set_cache
from constants.app_constants import (
    INDEXED_TABLE_NAME,
    TABLE_NAME,
    DEFAULT_PAGE,
    DEFAULT_PAGE_SIZE,
    ALLOWED_SORT_FIELDS,
    DEFAULT_SORT_FIELD,
    DEFAULT_SORT_ORDER
)

def serialize_postgres_row(row):
    for key, value in row.items():
        if isinstance(value, datetime):
            row[key] = value.isoformat()
        elif isinstance(value, Decimal):
            row[key] = float(value)
    return row

def standardize_column_name(col):
    return re.sub(r'[^a-zA-Z0-9_]', '', col.strip().lower().replace(" ", "_"))

def infer_type(values):
    for val in values:
        val = val.strip()
        if val == "":
            continue
        try:
            int(val)
        except:
            break
    else:
        return "INTEGER"

    for val in values:
        val = val.strip()
        if val == "":
            continue
        try:
            float(val)
        except:
            break
    else:
        return "FLOAT"

    lower_values = [v.lower().strip() for v in values if v]
    if all(v in ("true", "false") for v in lower_values):
        return "BOOLEAN"

    for val in values:
        val = val.strip()
        try:
            datetime.fromisoformat(val)
        except:
            break
    else:
        return "TIMESTAMP"

    return "TEXT"

def handle_postgres_bulk_upload_auto_infer(table_name: str, file: UploadFile) -> dict:
    try:
        content = file.file.read().decode("utf-8")
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)

        if not rows or len(rows) < 2:
            return {"error": "CSV must have header and data rows."}

        raw_headers = rows[0]
        data_rows = rows[1:]
        column_names = [standardize_column_name(h) for h in raw_headers]

        columns_data = list(zip(*data_rows))
        sample_limit = min(100, len(data_rows))

        inferred_types = [
            infer_type(col[:sample_limit]) for col in columns_data
        ]

        column_defs = ", ".join(
            f"{name} {dtype}" for name, dtype in zip(column_names, inferred_types)
        )

        create_table_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({column_defs});"
        placeholders = ", ".join(["%s"] * len(column_names))
        insert_sql = f"INSERT INTO {table_name} ({', '.join(column_names)}) VALUES ({placeholders})"

        conn = get_postgres_connection()
        cur = conn.cursor()

        cur.execute(create_table_sql)
        cur.executemany(insert_sql, data_rows)

        conn.commit()
        conn.close()

        return {
            "message": "Bulk upload successful.",
            "table": table_name,
            "columns": [
                {"name": n, "type": t} for n, t in zip(column_names, inferred_types)
            ],
            "inserted_rows": len(data_rows)
        }

    except Exception as e:
        return {"error": str(e)}

def fetch_upi_data_postgres(search: dict):
    filters = search.get("filter", {})
    pagination = search.get("pagination", {})
    sorting = search.get("sort", [])
    index_type = search.get("index_type", "indexed")
    include_facets = search.get("facets", False)
    query_text = search.get("query", "")

    table_name = INDEXED_TABLE_NAME if index_type == "indexed" else TABLE_NAME

    cache_key_raw = json.dumps(search, sort_keys=True)
    cache_key = "upi_pg_cache:" + hashlib.sha256(cache_key_raw.encode()).hexdigest()
    cached = get_cache(cache_key)
    if cached:
        return cached

    where_clauses = []
    params = []

    if query_text:
        where_clauses.append("search_vector @@ plainto_tsquery(%s)")
        params.append(query_text)

    if filters.get("sender_state"):
        where_clauses.append("sender_state = %s")
        params.append(filters["sender_state"])

    if filters.get("transaction_status"):
        where_clauses.append("transaction_status = %s")
        params.append(filters["transaction_status"])

    if filters.get("sender_bank"):
        where_clauses.append("sender_bank = %s")
        params.append(filters["sender_bank"])

    if filters.get("min_amount") is not None:
        where_clauses.append("amount_inr >= %s")
        params.append(filters["min_amount"])

    if filters.get("max_amount") is not None:
        where_clauses.append("amount_inr <= %s")
        params.append(filters["max_amount"])

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    limit = pagination.get("page_size", DEFAULT_PAGE_SIZE)
    page = pagination.get("page", DEFAULT_PAGE)
    offset = (page - 1) * limit

    sort_clause = "ORDER BY " + ", ".join(
        f"{rule['field']} {'ASC' if rule.get('order', 'asc') == 'asc' else 'DESC'}"
        for rule in sorting if rule.get("field") in ALLOWED_SORT_FIELDS
    ) if sorting else f"ORDER BY {DEFAULT_SORT_FIELD} {DEFAULT_SORT_ORDER.upper()}"

    query = f"""
        SELECT * FROM {table_name}
        {where_sql}
        {sort_clause}
        LIMIT %s OFFSET %s
    """
    params += [limit, offset]

    try:
        conn = get_postgres_connection()
        cur = conn.cursor()

        cur.execute(query, params)
        data = [serialize_postgres_row(dict(row)) for row in cur.fetchall()]

        count_query = f"SELECT COUNT(*) FROM {table_name} {where_sql}"
        cur.execute(count_query, params[:-2])  # Exclude limit & offset
        count = cur.fetchone()["count"]

        facets = {}
        if include_facets:
            for facet_field in ["sender_state", "sender_bank", "transaction_status"]:
                facet_query = f"""
                    SELECT {facet_field}, COUNT(*) as count
                    FROM {table_name}
                    {where_sql}
                    GROUP BY {facet_field}
                    ORDER BY count DESC
                """
                cur.execute(facet_query, params[:-2])
                facets[facet_field] = [dict(row) for row in cur.fetchall()]

        conn.close()

        result = {
            "data": data,
            "count": count,
            "page": page,
            "page_size": limit
        }

        if include_facets:
            result["facets"] = facets

        set_cache(cache_key, result)
        return result

    except Exception as e:
        return {"error": str(e)}
