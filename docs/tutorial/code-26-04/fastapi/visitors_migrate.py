# Adds database to FastAPI application

import os

import psycopg2

DATABASE_URI = os.environ["POSTGRESQL_DB_CONNECT_STRING"]

def migrate():
    with psycopg2.connect(DATABASE_URI) as conn, conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS visitors (
                timestamp TIMESTAMP NOT NULL,
                user_agent TEXT NOT NULL
            );
        """)
        conn.commit()


if __name__ == "__main__":
    migrate()
