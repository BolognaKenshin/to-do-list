from flask_wtf import FlaskForm
from wtforms import BooleanField, ColorField, StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired

# For Registering a new user
class NewUserForm(FlaskForm):
    email = StringField("E-mail Address", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired])
    submit = SubmitField("Sign up")
# For registered users to log in
class LoginForm(FlaskForm):
    email = StringField("E-mail Address", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired])
    submit = SubmitField("Log in")

# To generate the name of each to-do list, which will be the parent to items in the to-do items table
class ToDoNameForm(FlaskForm):
    to_do_name = StringField("List Name")
    # Placeholder below - want to let user click list name, press "Enter" to change
    # submit  = SubmitField("Enter Name")
    # date will be automatically applied via first submission

# To generate to-do items for each to-do list
class ToDoItemForm(FlaskForm):
    task = StringField()
    task_color = ColorField()
    task_importance = BooleanField("Important")
    task_complete = BooleanField("Task Complete?")
