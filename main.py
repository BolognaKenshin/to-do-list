from datetime import date
from flask import Flask, render_template
from flask_bootstrap import Bootstrap5
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from flask_sqlalchemy import SQLAlchemy
import os
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text, ForeignKey
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
login_manager = LoginManager()

app.config['SECRET_KEY'] = os.environ.get("FLASK_KEY")
Bootstrap5(app)

@app.route("/")
def homepage():
    return render_template("index.html")

@app.route("/sign-up", methods=["GET", "POST"])
def sign_up():
    return render_template("signup.html")

@app.route("/log-in", methods=["GET", "POST"])
def log_in():
    return render_template("login.html")

@app.route("/all-lists")
def all_lists():
    pass

@app.route("/list", methods=["GET", "POST"])
def current_list():
    pass

if __name__ == "__main__":
    app.run(debug=True)

