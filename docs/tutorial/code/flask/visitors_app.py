# Flask application that keeps track of visitors using a database

import datetime
import os

import flask
import psycopg2

app = flask.Flask(__name__)
app.config.from_prefixed_env()

DATABASE_URI = os.environ["POSTGRESQL_DB_CONNECT_STRING"]


@app.route("/")
def index():
    with psycopg2.connect(DATABASE_URI) as conn, conn.cursor() as cur:
        user_agent = flask.request.headers.get('User-Agent')
        timestamp = datetime.datetime.now()

        cur.execute(
            "INSERT INTO visitors (timestamp, user_agent) VALUES (%s, %s)",
            (timestamp, user_agent)
        )
        conn.commit()


    greeting = app.config.get("GREETING", "Hello, world!")
    return f"{greeting}\n"


@app.route("/visitors")
def visitors():
    with psycopg2.connect(DATABASE_URI) as conn, conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM visitors")
        total_visitors = cur.fetchone()[0]

    return f"{total_visitors}\n"


if __name__ == "__main__":
    app.run()
