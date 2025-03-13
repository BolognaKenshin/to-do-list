from flask import Flask, render_template
from flask_bootstrap import Bootstrap5
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
Bootstrap5(app)

@app.route("/")
def homepage():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)

