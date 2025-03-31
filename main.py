from flask import Flask, flash, redirect,render_template, request, session, url_for
from flask_bootstrap import Bootstrap5
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from forms import LoginForm, NewUserForm, ToDoNameForm
import os
import random
import string
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Table
from typing import List
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("FLASK_KEY")
login_manager = LoginManager()

class Base(DeclarativeBase):
    pass

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DB_URI", "sqlite:///to-dos.db")
db = SQLAlchemy(model_class=Base)
db.init_app(app)
login_manager.init_app(app)
Bootstrap5(app)

@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(Users, user_id)

relationships_table = Table(
    "relationships_table",
    Base.metadata,
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    Column("list_name_id", ForeignKey("list_names.id"), primary_key=True),
)

class Users(db.Model, UserMixin):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(250), nullable=False, unique=True)
    password: Mapped[str] = mapped_column(String(250), nullable=False)
    list_names: Mapped[List['ListName']] = relationship(secondary=relationships_table, back_populates="list_users")

class ListName(db.Model):
    __tablename__ = "list_names"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    list_name: Mapped[str] = mapped_column(String(250), nullable=False)
    list_users: Mapped[List['Users']] = relationship(secondary=relationships_table, back_populates="list_names")
    list_items: Mapped[List['ToDoItem']] = relationship()
    list_url_id: Mapped[str] = mapped_column(String(), nullable=False, unique=True)

class ToDoItem(db.Model):
    __tablename__ = "to_do_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item: Mapped[str] = mapped_column(String(250), nullable=False)
    list_name = relationship('ListName', back_populates='list_items')
    list_name_id: Mapped[int] = mapped_column(ForeignKey('list_names.id'))
    order_num: Mapped[int] = mapped_column(Integer, nullable=False)

with app.app_context():
    db.create_all()

# Generates a random series of characters, appends to a string 4-10 characters long
def generate_url_id(chars=string.ascii_letters + string.digits):
    id_length = random.randint(4, 10)
    list_name_urls = db.session.query(ListName.list_url_id).all()
    generated_id = ""
    for _ in range(id_length):
        generated_id += random.choice(chars)
    if any(generated_id == list_name_url[0] for list_name_url in list_name_urls):
        return generate_url_id()
    else:
        return generated_id


@app.route("/")
def homepage():
    return render_template("index.html")

@app.route("/sign-up", methods=["GET", "POST"])
def sign_up():
    form = NewUserForm()
    if form.validate_on_submit():
        result = db.session.execute(db.select(Users).where(Users.email == form.email.data))
        user = result.scalar()
        if user:
            flash("An account using that email already exists.")
            return redirect(url_for('log_in'))
        hs_password = generate_password_hash(password=request.form.get('password'), method='pbkdf2:sha256', salt_length=8)

        new_user = Users(
            email = request.form.get('email'),
            password = hs_password)

        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        print('registered and logging in!')
        return redirect(url_for('all_lists'))
    return render_template("signup.html", form=form)

@app.route("/log-in", methods=["GET", "POST"])
def log_in():
    form = LoginForm()
    if form.validate_on_submit():
        email = request.form.get('email')
        password = request.form.get('password')
        result = db.session.execute(db.select(Users).where(Users.email == email))
        user = result.scalar()
        if not user:
            flash("No account exists under the provided email address.")
        elif not check_password_hash(user.password, password):
            flash("The password entered is invalid.")
        else:
            login_user(user)
            print('logging in!')
            return redirect(url_for('all_lists'))
    return render_template("login.html", form=form)

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('log_in'))

@app.route("/all")
def all_lists():
    return render_template("lists.html", current_user=current_user)

@app.route("/list", methods=["GET", "POST"])
def current_list():
    pass

@app.route("/new-list", methods=["GET", "POST"])
def new_list():
    session['list_url_id'] = generate_url_id()
    form = ToDoNameForm()
    if form.validate_on_submit():
        session['list_name'] = form.to_do_name.data
    return render_template('new-list.html', current_user=current_user, form=form)

@app.route("/save-list", methods=["GET", "POST"])
def save_list():
    l_name = session['list_name']
    l_url_id = session['list_url_id']
    if not any(l_name == list_name.list_name for list_name in current_user.list_names):
        new_list_name = ListName(
            list_name=l_name,
            list_url_id=l_url_id,
        )
        db.session.add(new_list_name)
        db.session.commit()
        current_user.list_names.append(new_list_name)
        db.session.commit()
        return redirect(url_for("all_lists", current_user=current_user))
    else:
        flash("There is another list with that name registered to your account.")
    return redirect(url_for('all_lists'))

if __name__ == "__main__":
    app.run(debug=True)

