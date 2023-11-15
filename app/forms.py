from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, DateTimeField, FloatField, IntegerField, \
    SelectField
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
    audience = SelectField('Audience', choices=[(1, 'ALL'), (3, 'MANAGER+'), (8, 'VP+'), (10, 'C-SUITE')])

    # New Fields
    event_type = SelectField('Event Type', choices=[('company_hosted', 'Company Hosted'), ('third_party', '3rd Party')], validators=[DataRequired()])
    responsibility = SelectField('Responsibility for Attendance', choices=[('drive_attendance', 'Drive Attendance'), ('not_responsible', 'Not Responsible')], validators=[DataRequired()])
    registration_link = StringField('Registration Link', validators=[Optional()])
    city = StringField('City', validators=[DataRequired()])
    state = StringField('State', validators=[DataRequired()])
    industry = StringField('Industry', validators=[DataRequired()])
    audience_titles = StringField('Audience Titles', validators=[DataRequired()])  # Comma-separated or use checkboxes


    # Existing Fields
    cost = FloatField('Cost', validators=[Optional()])
    sponsor = StringField('Sponsor', validators=[Optional()])
    expected_attendees = IntegerField('Expected Attendees', validators=[Optional()])
    actual_attendees = IntegerField('Actual Attendees', validators=[Optional()])
    marketing_channel = StringField('Marketing Channel', validators=[Optional()])

    submit = SubmitField('Create Event')


class InvitationForm(FlaskForm):
    event_id = StringField('Event ID', validators=[DataRequired()])
    contact_id = StringField('Contact ID', validators=[DataRequired()])
    account_id = StringField('Account ID', validators=[DataRequired()])
    contact_title = StringField('Contact Title', validators=[DataRequired()])
    status = StringField('Status', validators=[DataRequired()])

    submit = SubmitField('Create Invitation')

