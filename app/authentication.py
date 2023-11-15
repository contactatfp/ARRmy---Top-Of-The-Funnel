from flask import Blueprint, redirect, url_for, request, flash, render_template
from flask_login import LoginManager, login_user, logout_user, login_required
from app.models import User, Account, RoleEnum
from app.forms import LoginForm, SignupForm
from app.tokens import get_user_token
from app.models import db
import requests
import os

consumer_key = os.getenv("CONSUMER_KEY")
consumer_secret = os.getenv("CONSUMER_SECRET")

auth_blueprint = Blueprint('auth', __name__)

login_manager = LoginManager()
# login_manager.init_app(app)
login_manager.login_view = 'auth.login'




def init_login_manager(app):
    login_manager.init_app(app)


@auth_blueprint.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        # Salesforce OAuth2 token endpoint
        url = "https://login.salesforce.com/services/oauth2/token"

        # Build payload with form input and Salesforce App credentials
        payload = {
            'grant_type': 'password',
            'client_id': consumer_key,
            'client_secret': consumer_secret,
            'username': username,
            'password': password
        }

        # Set headers for the POST request
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }

        # Send the POST request to Salesforce
        response = requests.request("POST", url, headers=headers, data=payload)

        # Check if Salesforce login is successful
        if response.status_code == 200:
            if not User.query.filter_by(username=form.username.data).first():
                url = "https://login.salesforce.com/services/oauth2/userinfo"
                token = get_user_token(form.username.data, form.password.data)
                token = token['access_token']
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {token}'
                }

                get_user_response = requests.get(url, headers=headers)
                # Create new user if user doesn't exist
                new_user = User(username=form.username.data)
                new_user.set_password(form.password.data)
                new_user.id = get_user_response.json()['user_id']
                db.session.add(new_user)
                db.session.commit()
                login_user(new_user)
                # get_data()
                # fix later
                return redirect(url_for('views.dash'))
            else:
                user = User.query.filter_by(username=form.username.data).first()
                login_user(user)
                accounts = Account.query.all()
                # Redirect to appropriate dashboard
                if user.role == RoleEnum.sales_rep:
                    return redirect(url_for('views.sales_dashboard'))
                elif user.role == RoleEnum.sdr:
                    return redirect(url_for('views.dash'))

                else:
                    return redirect(url_for('views.index'))
        if response.status_code == 302:
            return redirect(url_for('views.dash'))
        flash('Invalid username or password')
        return redirect(url_for('auth.login'))
    return render_template('login.html', form=form)


@auth_blueprint.route('/test_login', methods=['GET', 'POST'])
def test_login():
    name = "kloud101@gmail.com"
    pw = "Test1234"

    # Salesforce OAuth2 token endpoint
    url = "https://login.salesforce.com/services/oauth2/token"

    # Build payload with form input and Salesforce App credentials
    payload = {
        'grant_type': 'password',
        'client_id': consumer_key,
        'client_secret': consumer_secret,
        'username': name,
        'password': pw
    }

    # Set headers for the POST request
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json'
    }

    # Send the POST request to Salesforce
    response = requests.request("POST", url, headers=headers, data=payload)

    # Check if Salesforce login is successful
    if response.status_code == 200:

        if not User.query.filter_by(username=name).first():
            url = "https://login.salesforce.com/services/oauth2/userinfo"
            token = get_user_token(name, pw)
            token = token['access_token']
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }

            get_user_response = requests.get(url, headers=headers)
            # Create new user if user doesn't exist
            new_user = User(username=name)
            new_user.set_password(pw)
            new_user.id = get_user_response.json()['user_id']
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            # get_data()
            # fix later
            return redirect(url_for('views.dash'))
        else:
            user = User.query.filter_by(username=name).first()
            login_user(user)
            accounts = Account.query.all()
            # Redirect to appropriate dashboard
            if user.role == RoleEnum.sales_rep:
                return redirect(url_for('views.sales_dashboard'))
            elif user.role == RoleEnum.sdr:
                return redirect(url_for('views.dash'))

            else:
                return redirect(url_for('index'))
        flash('Invalid username or password')
        return redirect(url_for('auth.login'))
    return render_template('login.html')


@auth_blueprint.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('views.index'))


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


@auth_blueprint.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignupForm()
    if form.validate_on_submit():
        user = User(username=form.username.data)
        user.set_password(form.password.data)  # Hash the password before storing it
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('sign-up.html', form=form)
