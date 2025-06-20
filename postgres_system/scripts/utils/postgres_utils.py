import psycopg
from psycopg.rows import dict_row
from constants.app_configuration import config

def get_postgres_connection():
    try:
        conn = psycopg.connect(
            config.DATABASE_URL,
            row_factory=dict_row
        )
        return conn
    except Exception as e:
        print("Failed to connect to PostgreSQL:", str(e))
        raise

