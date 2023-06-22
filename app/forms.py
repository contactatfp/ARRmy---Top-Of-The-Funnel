from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


class SignupForm(FlaskForm):
    username = StringField(
        'Username', validators=[DataRequired(), Length(min=4, max=25)]
    )
    password = PasswordField(
        'Password',
        validators=[
            DataRequired(),
            EqualTo('confirm', message='Passwords must match')
        ],
    )
    confirm = PasswordField('Repeat Password')
    submit = SubmitField('Sign Up')
