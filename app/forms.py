from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, DateTimeField, FloatField, IntegerField
from wtforms.validators import DataRequired, Length, EqualTo, Optional


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


class EventForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    location = StringField('Location', validators=[DataRequired()])
    start_time = DateTimeField('Start Time', validators=[DataRequired()])
    end_time = DateTimeField('End Time', validators=[DataRequired()])
    audience = StringField('Audience', validators=[Optional()])
    event_type = StringField('Event Type', validators=[Optional()])
    cost = FloatField('Cost', validators=[Optional()])
    sponsor = StringField('Sponsor', validators=[Optional()])
    expected_attendees = IntegerField('Expected Attendees', validators=[Optional()])
    actual_attendees = IntegerField('Actual Attendees', validators=[Optional()])
    marketing_channel = StringField('Marketing Channel', validators=[Optional()])

    submit = SubmitField('Create Event')
