from flask import Flask

app = Flask(__name__)

@app.route("/")
def homepage():
    pass


if __name__ == "__main__":
    app.run()

