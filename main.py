from flask import Flask, flash, redirect,render_template, request, session, url_for
from flask_bootstrap import Bootstrap5
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from forms import LoginForm, NewUserForm, ToDoItemForm, ToDoNameForm
import os
import random
import string
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Boolean, Column, Integer, String, Text, ForeignKey, Table
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

def login_required(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated:
            return func(*args, **kwargs)
        return redirect(url_for('log_in'))
    return decorated_function

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
    list_items: Mapped[List['ToDoItem']] = relationship(cascade="all, delete-orphan")
    list_url_id: Mapped[str] = mapped_column(String(), nullable=False, unique=True)

# Pulled via relationship with list name
class ToDoItem(db.Model):
    __tablename__ = "to_do_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item: Mapped[str] = mapped_column(String(250), nullable=False)
    list_name = relationship('ListName', back_populates='list_items')
    list_name_id: Mapped[int] = mapped_column(ForeignKey('list_names.id'))
    order_num: Mapped[int] = mapped_column(Integer, nullable=False)
    is_important: Mapped[bool] = mapped_column(Boolean)
    is_done: Mapped[bool] = mapped_column(Boolean)

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
    error = request.args.get('error_message')
    if form.validate_on_submit():
        try:
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
            return redirect(url_for('all_lists'))
        except Exception:
            e = "An unexpected error has occurred. Please try again."
            return redirect(url_for('sign_up', error_message=e))
    return render_template("signup.html", form=form, error_message=error)

@app.route("/log-in", methods=["GET", "POST"])
def log_in():
    form = LoginForm()
    e = request.args.get('error_message')
    if form.validate_on_submit():
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            result = db.session.execute(db.select(Users).where(Users.email == email))
            user = result.scalar()
            if not user:
                flash("No account exists under the provided email address.")
            elif not check_password_hash(user.password, password):
                flash("The password entered is invalid.")
            else:
                login_user(user)
                return redirect(url_for('all_lists'))
        except Exception:
            e = "An unexpected error has occurred. Please try again."
            return redirect(url_for('log_in', error_message=e))
    return render_template("login.html", form=form, error_message=e)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('log_in'))

# Route for displaying all lists user has generated
@app.route("/all")
@login_required
def all_lists():
    error_message=request.args.get('error_message')
    session['list_items'] = []
    ongoing_lists = []
    finished_lists = []
    session['first_access'] = True
    for list in current_user.list_names:
        if not any(item.is_done == False for item in list.list_items):
            finished_lists.append(list)
        else:
            ongoing_lists.append(list)
    return render_template("lists.html", current_user=current_user, finished_lists=finished_lists, ongoing_lists=ongoing_lists, error_message=error_message)

# Generated page for naming the list - Checks if the name exists before letting you submit and go to new_list()
# List name is stored in flask session
@app.route("/name-list", methods=["GET", "POST"])
@login_required
def name_list():
    rename = request.args.get('rename')
    name_form = ToDoNameForm()
    if name_form.validate_on_submit():
        l_name = name_form.to_do_name.data

        # Checking if a list is being renamed or if a new list is being made via 'rename' variable from 'edit-list.html'
        if not rename == 'rename':
            session['list_name'] = name_form.to_do_name.data
            return redirect(url_for('new_list'))
        else:
            list_url_id = request.args.get('list_url_id')
            try:
                session['list_name'] = l_name
                return redirect(url_for('edit_list', list_url_id=list_url_id))
            except Exception as e:
                error_message = "An unexpected error has occurred. Please try again"
                return redirect(url_for('all_lists', error_message=error_message))
    return render_template('name-list.html', current_user=current_user, name_form=name_form, rename=rename)

# Generated after naming your list, lets you create to-do items - Stores them in flask session
@app.route("/new-list", methods=["GET", "POST"])
@login_required
def new_list():
    item_form = ToDoItemForm()
    if item_form.validate_on_submit():
        new_item = {"task":item_form.task.data,
                    "importance": False,
                    "finished": False,}
        session['list_items'].append(new_item)
        session.modified = True
    return render_template('new-list.html',
                           current_user=current_user,
                           list_name=session['list_name'],
                           item_form=item_form,
                           tasks=session['list_items'])


# Page for editing an existing list - Add new items - Rename list
@app.route("/edit-list/<list_url_id>", methods=["GET", "POST"])
@login_required
def edit_list(list_url_id):
    item_form = ToDoItemForm()
    if session['first_access'] == True:
        try:
            list_to_edit = db.session.execute(db.Select(ListName).where(ListName.list_url_id == list_url_id)).scalar()
            session['first_access'] = False
            session['list_url_id'] = list_url_id
            session['list_name'] = list_to_edit.list_name
            session['list_items'] = []
            for task in list_to_edit.list_items:
                item = {"task": task.item,
                        "importance": task.is_important,
                        "finished": task.is_done,
                        "order_num": task.order_num,}
                session['list_items'].append(item)
        except Exception as e:
            error_message = "An unexpected error has occurred. Please try again"
            return redirect(url_for('all_lists', error_message=error_message))

    if item_form.validate_on_submit():
        new_item = {"task": item_form.task.data,
                    "order_num": len(session['list_items']),
                    "importance": False,
                    "finished": False, }
        session['list_items'].append(new_item)
        session.modified = True

    current_url = request.url
    return render_template('edit-list.html', current_user=current_user, list_name=session['list_name'],
                           item_form=item_form, tasks=session['list_items'], current_url=current_url, list_url_id=session['list_url_id'])


# Route for saving a new list
@app.route("/save-list", methods=["GET", "POST"])
@login_required
def save_list():
    is_new_list = request.args.get('new_list')
    l_name = session['list_name']
    # If a new list is being saved, variable is defined from 'new-list.html'
    if is_new_list == "True":
        try:
            session['list_url_id'] = generate_url_id()
            l_url_id = session['list_url_id']
            new_list_name = ListName(
                list_name=l_name,
                list_url_id=l_url_id,
            )
            current_user.list_names.append(new_list_name)

            # Save index is to properly reference ascending item names (item 1, item 2, item 3)
            save_index = 0
            for item in session['list_items']:
                new_item = ToDoItem(
                    item=item['task'],
                    list_name=new_list_name,
                    order_num=save_index,
                    is_important=False,
                    is_done=False,
                )
                db.session.add(new_item)
                save_index += 1
        except Exception:
            error_message = "An unexpected error has occurred. Please try again"
            return redirect(url_for('all_lists', error_message=error_message))
    # If new_list is "False," which is set in 'edit-list.html'
    else:
        try:
            list_to_edit = db.session.execute(db.Select(ListName).where(ListName.list_url_id == session['list_url_id'])).scalar()
            if list_to_edit not in current_user.list_names:
                db.session.execute(relationships_table.insert().values(
                    user_id=current_user.id,
                    list_name_id=list_to_edit.id,
                ))
            list_to_edit.list_name = session['list_name']
            # This section triggers when saving a list after deleting items.
            if len(list_to_edit.list_items) > len(session['list_items']):
                for i in range(len(list_to_edit.list_items)):
                    if i < len(session['list_items']):
                        continue
                    else:
                        db.session.delete(list_to_edit.list_items[i])
            for i in range(len(session['list_items'])):
                # To catch if there are more tasks being saved to an existing list
                if i < len(list_to_edit.list_items):
                    item = list_to_edit.list_items[i]
                    item.item = session['list_items'][i]['task']
                    item.is_important= session['list_items'][i]['importance']
                    item.is_done = session['list_items'][i]['finished']
                    item.order_num = session['list_items'][i]['order_num']
                else:
                    new_item = ToDoItem(
                        item=session['list_items'][i]['task'],
                        list_name=list_to_edit,
                        order_num=session['list_items'][i]['order_num'],
                        is_important=session['list_items'][i]['importance'],
                        is_done=session['list_items'][i]['finished']
                    )
                    db.session.add(new_item)
        except Exception:
            error_message = "An unexpected error has occurred. Please try again"
            return redirect(url_for('all_lists', error_message=error_message))
    db.session.commit()
    return redirect(url_for("all_lists", current_user=current_user))

# Deletes parent ListName and ToDoItems children along with it via cascade defined in relationship
@app.route("/delete-list", methods=["GET"])
@login_required
def delete_list():
    list_id = request.args.get('list_name_id')
    try:
        list_to_delete = db.get_or_404(ListName, list_id)
        db.session.delete(list_to_delete)
        db.session.commit()
    except Exception:
        error_message = "An unexpected error has occurred. Please try again"
        return redirect(url_for('all_lists', error_message=error_message))
    return redirect(url_for('all_lists'))

@app.route("/change-importance")
@login_required
def change_importance():
    task_index = int(request.args.get('task_index'))
    if session['list_items'][task_index]['importance'] == False:
        session['list_items'][task_index]['importance'] = True
    else:
        session['list_items'][task_index]['importance'] = False
    session.modified = True
    return redirect(url_for('edit_list', list_url_id=session['list_url_id'], first_access=False))

@app.route("/delete-task", methods=["GET"])
@login_required
def delete_task():
    is_new_list = request.args.get('new_list')
    item_form = ToDoItemForm()
    if is_new_list == "True":
        task_index = int(request.args.get('task_index'))
        session['list_items'].pop(task_index)
        session.modified = True
        return redirect(url_for('new_list', current_user=current_user,
                               list_name=session['list_name'],
                               item_form=item_form,
                               tasks=session['list_items']))
    else:
        task_index = int(request.args.get('task_index'))
        session['list_items'].pop(task_index)
        session.modified = True
        return redirect(url_for('edit_list', list_url_id=session['list_url_id'],  first_access=False))

@app.route("/task-done")
@login_required
def mark_as_completed():
   task_index = int(request.args.get('task_index'))
   if session['list_items'][task_index]['finished'] == False:
       session['list_items'][task_index]['finished'] = True
   else:
       session['list_items'][task_index]['finished'] = False
   session.modified=True
   return redirect(url_for('edit_list', list_url_id=session['list_url_id'], first_access=False))

@app.route('/update_task_order', methods=['POST'])
@login_required
def update_task_order():
    data = request.get_json()
    new_order = []
    task_order = data.get('task_order', [])
    for task_index in task_order:
        for task in session['list_items']:
            if int(task_index) == task['order_num']:
                new_order.append(task)
                session['list_items'].remove(task)
    for task in session['list_items']:
        if task['finished']:
            new_order.append(task)
        elif task['importance']:
            new_order.insert(0, task)
    session['list_items'] = new_order
    return redirect(url_for('edit_list', list_url_id=session['list_url_id'], first_access=False))

if __name__ == "__main__":
    app.run(debug=True)

