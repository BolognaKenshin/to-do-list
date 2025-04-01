import datetime
from flask_wtf import FlaskForm
from wtforms import BooleanField, ColorField, StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired

now = datetime.datetime.now()
formatted_date= now.strftime("%m/%d/%y")

# For Registering a new user
class NewUserForm(FlaskForm):
    email = StringField("E-mail Address", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Sign up")
# For registered users to log in
class LoginForm(FlaskForm):
    email = StringField("E-mail Address", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Log in")

# To generate the name of each to-do list, which will be the parent to items in the to-do items table
class ToDoNameForm(FlaskForm):
    to_do_name = StringField("", default=f"My List - {formatted_date}", validators=[DataRequired()])
    # Placeholder below - want to let user click list name, press "Enter" to change
    # submit  = SubmitField("Enter Name")
    # date will be automatically applied via first submission

# To generate to-do items for each to-do list
class ToDoItemForm(FlaskForm):
    task = StringField("", validators=[DataRequired()])
    # task_color = ColorField()
    # task_importance = BooleanField("Important")
    # task_complete = BooleanField("Task Complete?")
