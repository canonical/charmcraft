from time import sleep

import flask

app = flask.Flask(__name__)


@app.route("/")
def index():
    return "Hello, world!\n"


@app.route("/io")
def pseudo_io():
    sleep(2)
    return "ok\n"

if __name__ == "__main__":
    app.run()
