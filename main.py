from flask import Flask, flash, redirect,render_template, request, session, url_for
from flask_bootstrap import Bootstrap5
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from forms import LoginForm, NewUserForm, ToDoItemForm, ToDoNameForm
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


# Holds relationships between multiple users to a list name
relationships_table = Table(
    "relationships_table",
    Base.metadata,
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    Column("list_name_id", ForeignKey("list_names.id"), primary_key=True),
)

# Multiple users can have a relationship with a list name
class Users(db.Model, UserMixin):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(250), nullable=False, unique=True)
    password: Mapped[str] = mapped_column(String(250), nullable=False)
    list_names: Mapped[List['ListName']] = relationship(secondary=relationships_table, back_populates="list_users")

# List names will pull the ToDoItems
class ListName(db.Model):
    __tablename__ = "list_names"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    list_name: Mapped[str] = mapped_column(String(250), nullable=False)
    list_users: Mapped[List['Users']] = relationship(secondary=relationships_table, back_populates="list_names")
    list_items: Mapped[List['ToDoItem']] = relationship()
    list_url_id: Mapped[str] = mapped_column(String(), nullable=False, unique=True)

# Pulled via relationship with list name
class ToDoItem(db.Model):
    __tablename__ = "to_do_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item: Mapped[str] = mapped_column(String(250), nullable=False)
    list_name = relationship('ListName', back_populates='list_items')
    list_name_id: Mapped[int] = mapped_column(ForeignKey('list_names.id'))
    order_num: Mapped[int] = mapped_column(Integer, nullable=False)

with app.app_context():
    db.create_all()

# Generates a random series of characters, returns a random string 4-10 characters long meant to be assigned to list names
# Function also checks if the id exists already in the database, will run again until it finds one not used
def generate_url_id(chars=string.ascii_letters + string.digits):
    id_length = random.randint(4, 10)
    generated_id = ""
    for _ in range(id_length):
        generated_id += random.choice(chars)
    list_name_urls = db.session.execute(db.Select(ListName.list_url_id)).scalars().all()
    if any(generated_id == list_name_url for list_name_url in list_name_urls):
        return generate_url_id()
    else:
        return generated_id


@app.route("/")
def homepage():
    if current_user.is_authenticated:
        return redirect(url_for('all_lists'))
    return render_template("index.html")

# For new users - Salts and hashes their password, stores in a database
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

# Route for displaying all lists user has generated
@app.route("/all")
def all_lists():
    session['list_items'] = []
    return render_template("lists.html", current_user=current_user)

# Generated page for naming the list - Checks if the name exists before letting you submit and go to new_list()
# List name is stored in flask session
@app.route("/name-list", methods=["GET", "POST"])
def name_list():
    name_form = ToDoNameForm()
    session['list_items'] = []
    if name_form.validate_on_submit():
        l_name = name_form.to_do_name.data
        # Check for if user already has a list with the same name
        if not any(l_name == list_name.list_name for list_name in current_user.list_names):
            session['list_name'] = name_form.to_do_name.data
            return redirect(url_for('new_list'))
        else:
            flash("There is another list with that name registered to your account.")
    return render_template('name-list.html', current_user=current_user, name_form=name_form)

# Generated after naming your list, lets you create to-do items - Stores them in flask session
@app.route("/new-list", methods=["GET", "POST"])
def new_list():
    item_form = ToDoItemForm()
    displayed_items = []
    if item_form.validate_on_submit():
        new_item = {f"item {len(session['list_items']) + 1}": {"task": item_form.task.data}}
        session['list_items'].append(new_item)
        session.modified = True
        index = 1
        for item in session['list_items']:
            displayed_items.append(item[f'item {index}']['task'])
            index += 1
    return render_template('new-list.html',
                           current_user=current_user,
                           list_name=session['list_name'],
                           item_form=item_form,
                           tasks=displayed_items)


# Page for editing an existing list - Add new items - Rename list
@app.route("/edit-list/<list_url_id>", methods=["GET", "POST"])
def edit_list(list_url_id):
    item_form = ToDoItemForm()
    list_to_edit = db.session.execute(db.Select(ListName).where(ListName.list_url_id == list_url_id)).scalar()
    session['list_url_id'] = list_url_id
    session['list_name'] = list_to_edit.list_name
    session['list_items'] = []
    for task in list_to_edit.list_items:
        session['list_items'].append(task.item)
    if item_form.validate_on_submit():
        new_item = {"task": item_form.task.data}
        session['list_items'].append(new_item['task'])
        session.modified = True
    return render_template('edit-list.html', current_user=current_user, list_name=list_to_edit.list_name,
                           item_form=item_form, tasks=session['list_items'])



# Route for saving a new list
@app.route("/save-new-list", methods=["GET", "POST"])
def save_new_list():
    is_new_list = request.args.get('new_list')
    l_name = session['list_name']
    if is_new_list == "True":
        print('new list!')
        session['list_url_id'] = generate_url_id()
        l_url_id = session['list_url_id']
        new_list_name = ListName(
            list_name=l_name,
            list_url_id=l_url_id,
        )
        current_user.list_names.append(new_list_name)

        # Save index is to properly reference ascending item names (item 1, item 2, item 3)
        save_index = 1
        for item in session['list_items']:
            new_item = ToDoItem(
                item=item[f'item {save_index}']['task'],
                list_name=new_list_name,
                order_num=save_index
            )
            db.session.add(new_item)
            save_index += 1
    else:
        list_to_edit = db.session.execute(db.Select(ListName).where(ListName.list_url_id == session['list_url_id'])).scalar()
        list_to_edit.list_name = session['list_name']
        save_index = 1
        for i in range(len(session['list_items'])):
            if i < len(list_to_edit.list_items):
                item = list_to_edit.list_items[i]
                item.item = session['list_items'][i]
                save_index += 1
            else:

                new_item = ToDoItem(
                    item=session['list_items'][i],
                    list_name=list_to_edit,
                    order_num=save_index
                )
                db.session.add(new_item)
                save_index += 1

    db.session.commit()
    return redirect(url_for("all_lists", current_user=current_user))


if __name__ == "__main__":
    app.run(debug=True)

