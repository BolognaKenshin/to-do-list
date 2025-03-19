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
app.config['SECRET_KEY'] = os.environ.get("FLASK_KEY")
login_manager = LoginManager()

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
db.init_app(app)
Bootstrap5(app)


class User(db.Model):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

class ListName(db.Model):
    __tablename__ = "list_name"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

class ToDoItem(db.Model):
    __tablename__ = "to_do_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

class Relationship(db.Model):
    __tablename__ = "relationship_table"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

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

