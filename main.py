import json

import requests
from dateutil.parser import parse
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from sqlalchemy import DateTime

from app.forms import SignupForm, LoginForm
from app.models import db, User, RoleEnum, init_db, Account
from flask_migrate import Migrate

app = Flask(__name__)

migrate = Migrate(app, db)

# Configure your app
app.config.from_object('app.config')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key'

# Initialize the database
init_db(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

with open('config.json') as f:
    config = json.load(f)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


@app.route('/')
def index():  # put application's code here
    get_data()
    # if user is logged in, redirect to appropriate dashboard
    if current_user.is_authenticated:
        if current_user.role == RoleEnum.sales_rep:
            return redirect(url_for('sales_dashboard'))
        elif current_user.role == RoleEnum.sdr:
            return redirect(url_for('sdr_dashboard', accounts=Account.query.all()))
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        # Salesforce OAuth2 token endpoint
        url = "https://login.salesforce.com/services/oauth2/token"

        # Build payload with form input and Salesforce App credentials
        payload = {
            'grant_type': 'password',
            'client_id': config['consumer-key'],
            'client_secret': config['consumer-secret'],
            'username': form.username.data,
            'password': form.password.data
        }

        # Set headers for the POST request
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }

        # Send the POST request to Salesforce
        response = requests.post(url, headers=headers, data=payload)

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
            else:
                user = User.query.filter_by(username=form.username.data).first()
                login_user(user)
                # Redirect to appropriate dashboard
                if user.role == RoleEnum.sales_rep:
                    return redirect(url_for('sales_dashboard'))
                elif user.role == RoleEnum.sdr:
                    return redirect(url_for('sdr_dashboard', accounts=Account.query.all()))

                else:
                    return redirect(url_for('index'))
        flash('Invalid username or password')
        return redirect(url_for('login'))
    return render_template('login.html', form=form)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignupForm()
    if form.validate_on_submit():
        user = User(username=form.username.data)
        user.set_password(form.password.data)  # Hash the password before storing it
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('signup.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/sales_dashboard')
@login_required
def sales_dashboard():
    # Check if the logged-in user is a sales representative
    if current_user.role == RoleEnum.sales_rep:
        return render_template('sales_dashboard.html')
    return "Access denied", 403


@app.route('/sdr_dashboard')
@login_required
def sdr_dashboard():
    # Check if the logged-in user is an SDR
    accounts = Account.query.all()
    print(accounts)
    if current_user.role == RoleEnum.sdr:
        return render_template('sdr_dashboard.html', accounts=accounts)
    return "Access denied", 403


DOMAIN = "https://fakepicasso-dev-ed.develop.my.salesforce.com"


def tokens():
    try:
        payload = {
            'grant_type': 'password',
            'client_id': config['consumer-key'],
            'client_secret': config['consumer-secret'],
            'username': 'contact@fakepicasso.com',
            'password': config['sf-pw']
        }
        oauth_endpoint = f"{DOMAIN}/services/oauth2/token"
        response = requests.post(oauth_endpoint, data=payload)

        if response.status_code == 200:
            return response.json()
        else:
            print("Error in token retrieval:", response.text)
            return None
    except Exception as e:
        print("Exception in tokens function:", str(e))
        return None


def get_user_token(username, pw):
    try:
        payload = {
            'grant_type': 'password',
            'client_id': config['consumer-key'],
            'client_secret': config['consumer-secret'],
            'username': username,
            'password': pw
        }
        oauth_endpoint = f"{DOMAIN}/services/oauth2/token"
        response = requests.post(oauth_endpoint, data=payload)

        if response.status_code == 200:
            return response.json()
        else:
            print("Error in token retrieval:", response.text)
            return None
    except Exception as e:
        print("Exception in tokens function:", str(e))
        return None


def get_data():
    try:
        token = tokens()
        if token is None:
            return {"error": "Failed to get Salesforce token"}

        print(token['access_token'])
        access_token = token['access_token']

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        endpoint = '/services/data/v58.0/query/'
        records = []

        params = {'q': soql_query()}
        response = requests.get(DOMAIN + endpoint, headers=headers, params=params)

        print("Response from Salesforce:", response.json())

        if 'totalSize' in response.json() and 'records' in response.json():
            total_size = response.json()['totalSize']
            records.extend(response.json()['records'])

            while 'nextRecordsUrl' in response.json():
                next_records_url = response.json()['nextRecordsUrl']
                response = requests.get(DOMAIN + next_records_url, headers=headers)
                records.extend(response.json()['records'])

            for record in records:
                # Create an empty Account object
                account = Account()

                # Assign each field from the record to the corresponding attribute in the Account object
                for key, value in record.items():
                    # Check if the key is an attribute of the Account class
                    if hasattr(account, key):
                        # Special handling for 'SLAExpirationDate__c'
                        if key in ['CreatedDate', 'SLAExpirationDate__c', 'LastModifiedDate', 'LastViewedDate',
                                   'LastReferencedDate'] and value is not None:
                            value = parse(value)
                        # Check if the current column is a DateTime column
                        elif isinstance(getattr(Account, key).property.columns[0].type, DateTime) and value is not None:
                            value = parse(value)

                        setattr(account, key, value)

                # Check if the record already exists
                existing_account = Account.query.filter_by(Id=account.Id).first()
                # If the record doesn't exist, insert it
                if existing_account is None:
                    try:
                        db.session.add(account)
                        db.session.commit()
                    except Exception as e:
                        # Optionally log the error and rollback the transaction
                        db.session.rollback()
                        print(f"Error inserting account: {e}")

            return {'record_size': total_size, 'records': records}
        else:
            return {"error": "Unexpected response format from Salesforce"}
    except Exception as e:
        print("Exception in get_data function:", str(e))
        return {"error": "An error occurred while retrieving data"}


@app.route('/add_account', methods=['POST'])
@login_required
def add_account():
    # Parse JSON data from the request
    data = request.json
    name = data['name']
    street = data['street']
    city = data['city']
    state = data['state']
    zip = data['zip']

    token = tokens()
    token = token['access_token']
    url = "https://fakepicasso-dev-ed.develop.my.salesforce.com/services/data/v58.0/sobjects/account"
    payload = json.dumps({
        "Name": name,
        "BillingStreet": street,
        "BillingCity": city,
        "BillingState": state,
        "BillingPostalCode": zip
    })
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    print(response.text)
    if response.status_code == 201:
        # print('Account successfully added')
        get_data()
        return jsonify({"success": True})
    else:
        # print('Error adding account')
        return jsonify({"success": False})


def soql_query():
    # Make sure the query is properly formatted without the '+' characters
    soql_query = "SELECT FIELDS (All) FROM Account LIMIT 200"
    return soql_query


@app.route('/contacts', methods=['GET'])
def contacts():
    response = fetch_contacts()
    contacts = response["data"]["uiapi"]["query"]["Contact"]["edges"]
    return render_template('contacts.html', contacts=contacts)


def fetch_contacts():
    url = "https://fakepicasso-dev-ed.develop.my.salesforce.com/services/data/v58.0/graphql"

    payload = json.dumps({
        "query": """query contactsByTheirAccountName {
                        uiapi {
                            query {
                                Contact(orderBy: { Account: { Name: { order: DESC } } }) {
                                    edges {
                                        node {
                                            Id
                                            Name {
                                                value
                                            }
                                            Account {
                                                Name {
                                                    value
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }""",
        "variables": {}
    })

    token = tokens()
    token = token['access_token']

    headers = {
        'X-Chatter-Entity-Encoding': 'false',
        'Content-Type': 'application/json',
        'Authorization': f"Bearer {token}",
    }
    response = requests.post(url, headers=headers, data=payload)

    return response.json()


if __name__ == '__main__':
    app.run()
