# Flask app with a greeting configuration

import flask

app = flask.Flask(__name__)
app.config.from_prefixed_env()


@app.route("/")
def index():
    greeting = app.config.get("GREETING", "Hello, world!")
    return f"{greeting}\n"


if __name__ == "__main__":
    app.run()
