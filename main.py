import json
from datetime import datetime

import requests
from dateutil.parser import parse
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from sqlalchemy import DateTime

from app.forms import SignupForm, LoginForm
from app.models import db, User, RoleEnum, init_db, Account, Contact, Interaction, Event
from flask_migrate import Migrate
from app.forms import EventForm

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

DOMAIN = "https://fakepicasso-dev-ed.develop.my.salesforce.com"


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

    def get_last_interaction(accountId):
        interaction = Interaction.query.filter_by(account_id=accountId).order_by(Interaction.timestamp.desc()).first()
        return interaction

    # def get_last_interaction(accountId):
    #     date = Interaction.query.filter_by(account_id=accountId).order_by(Interaction.timestamp.desc()).first()
    #     current_date = datetime.now()
    #     if date is None:
    #         return None
    #     # return the rounded number of days since the last interaction
    #     return date.timestamp

    if current_user.role == RoleEnum.sdr:
        return render_template('sdr_dashboard.html', accounts=accounts, get_last_interaction=get_last_interaction)
    return "Access denied", 403


from datetime import datetime

@app.route('/events_page')
def events_page():
    # Retrieve all events from the database
    # with app.context
    with app.app_context():
        events = Event.query.all()

    # Render the events page and pass the events to the template
    return render_template('events_page.html', events=events)


@app.route('/add_event', methods=['GET', 'POST'])
def add_event():
    form = EventForm()
    if form.validate_on_submit():
        # Add new event to the database here
        # Then redirect to the events page or some other page
        return redirect(url_for('events_page'))
    return render_template('add_event.html', form=form)


def time_since_last_interaction(last_interaction_timestamp):
    now = datetime.now()
    difference = now - last_interaction_timestamp
    days_difference = difference.days

    if days_difference == 0:
        return 'Today'
    elif days_difference < 7:
        return f'{days_difference} days ago'
    elif days_difference < 30:
        weeks_difference = days_difference // 7
        return f'{weeks_difference} weeks ago'
    else:
        months_difference = days_difference // 30
        return f'{months_difference} months ago'


app.jinja_env.filters['time_since'] = time_since_last_interaction


@app.route('/interaction_details/<int:interaction_id>')
def interaction_details(interaction_id):
    interaction = Interaction.query.get_or_404(interaction_id)
    account = Account.query.get(interaction.account_id)
    contact = Contact.query.get(interaction.contactId)
    return render_template('interaction_details.html', interaction=interaction, account=account, contact=contact,
                           interaction_id=interaction_id)


# @app.route('/interaction/<int:interaction_id>')
# @login_required
# def interaction_details(interaction_id):
#     interaction = Interaction.query.get_or_404(interaction_id)
#     account = Account.query.get(interaction.account_id)
#     contact = Contact.query.get(interaction.contact_id)
#     return render_template('interaction_details.html', interaction=interaction, account=account, contact=contact)


@app.route('/account/<id>')
@login_required
def account(id):
    account = Account.query.filter_by(id=id).first()
    contacts = Contact.query.filter_by(account_id=id).all()
    interactions = Interaction.query.filter_by(account_id=id).all()
    return render_template('account.html', account=account, contacts=contacts, interactions=interactions)


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

        access_token = token['access_token']

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        endpoint = '/services/data/v58.0/query/'
        records = []

        params = {'q': soql_query("SELECT+FIELDS(All) FROM Account LIMIT 200")}
        response = requests.get(DOMAIN + endpoint, headers=headers, params=params)

        # print("Response from Salesforce:", response.json())

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


def soql_query(query):
    # Make sure the query is properly formatted without the '+' characters
    soql_query = query.replace('+', ' ')
    return soql_query


@app.route('/contacts', methods=['GET'])
def contacts():
    response = fetch_contacts()
    contacts = []

    # Iterate through each item in the data
    for item in response['records']:
        # Extract the attributes from item based on fields defined in models.py
        contact = {
            'Id': item.get('Id'),
            'AccountId': item.get('AccountId'),
            'LastName': item.get('LastName'),
            'FirstName': item.get('FirstName'),
            'Salutation': item.get('Salutation'),
            'Name': item.get('Name'),
            'MailingStreet': item.get('MailingStreet'),
            'MailingCity': item.get('MailingAddress', {}).get('city') if item.get('MailingAddress') else None,
            'MailingState': item.get('MailingAddress', {}).get('state') if item.get('MailingAddress') else None,
            'MailingPostalCode': item.get('MailingAddress', {}).get('postalCode') if item.get(
                'MailingAddress') else None,
            'MailingCountry': item.get('MailingAddress', {}).get('country') if item.get('MailingAddress') else None,

            'Phone': item.get('Phone'),
            'Fax': item.get('Fax'),
            'MobilePhone': item.get('MobilePhone'),
            'Email': item.get('Email'),
            'Title': item.get('Title'),
            'Department': item.get('Department'),
            'AssistantName': item.get('AssistantName'),
            'Birthdate': item.get('Birthdate'),
            'OwnerId': item.get('OwnerId'),
            'CreatedDate': item.get('CreatedDate'),
            'LastModifiedDate': item.get('LastModifiedDate')
        }
        # Append the contact object to the contacts list
        contacts.append(contact)
    return render_template('contacts.html', contacts=contacts)


def fetch_contacts():
    endpoint = '/services/data/v58.0/query/'
    url = DOMAIN + endpoint

    token = tokens()
    token = token['access_token']

    headers = {
        'X-Chatter-Entity-Encoding': 'false',
        'Content-Type': 'application/json',
        'Authorization': f"Bearer {token}",
    }
    response = requests.request("GET", url, headers=headers,
                                params={'q': soql_query("SELECT+FIELDS(All)+FROM+Contact LIMIT 200")})
    contact_data = response.json()

    # Import contacts into the database
    for record in contact_data['records']:

        # Create a new Contact object with the data from the current record
        contact = Contact(
            Id=record['Id'],
            AccountId=record['AccountId'],
            LastName=record['LastName'],
            FirstName=record['FirstName'],
            Salutation=record['Salutation'],
            Name=record['Name'],
            MailingStreet=record['MailingStreet'],
            MailingCity=record['MailingCity'],
            MailingState=record['MailingState'],
            MailingPostalCode=record['MailingPostalCode'],
            Phone=record['Phone'],
            Email=record['Email']

        )

        if Contact.query.filter_by(Id=contact.Id).first() is None:
            db.session.add(contact)

    # Commit the changes
    db.session.commit()

    return contact_data


def id2Name(id):
    account = Account.query.filter_by(Id=id).first()
    return account.Name


@app.route('/logACall', methods=['POST'])
def logACall():
    data = request.json
    description = data.get('description')
    accountId = data.get('accountId')
    subject = data.get('subject')
    contactId = data.get('contactId')
    token = tokens()
    if token is None:
        return {"error": "Failed to get Salesforce token"}

    # print(token['access_token'])
    access_token = token['access_token']

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    endpoint = '/services/data/v58.0/sobjects/Task'
    body = {
        "Subject": subject,
        "Description": description,
        "CallType": "Outbound",
        "Status": "Closed",
        "WhoID": contactId,
        "TaskSubtype": "call"
    }

    response = requests.post(DOMAIN + endpoint, headers=headers, data=json.dumps(body))
    print(response.json())

    # add log a call to database under interactions
    interaction = Interaction(
        account_id=accountId,
        description=description,
        contactId=contactId,
        timestamp=datetime.now(),
        interaction_type="call",
        user_id=current_user.id
    )
    db.session.add(interaction)
    db.session.commit()

    if response.status_code == 201:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False})


@app.route('/getContacts', methods=['GET'])
def get_contacts():
    account_id = request.args.get('accountId')

    # Query your database or API to get contacts associated with the account_id
    # This is a placeholder. You'll need to implement this based on how your data is stored.
    # account_name = Account.query.filter_by(Id=account_id).first().Name
    contacts = Contact.query.filter_by(AccountId=account_id).all()

    # Convert the Contact objects to dictionaries
    contacts_list = [convert_contact_to_dict(contact) for contact in contacts]

    # Return contacts in JSON format
    return jsonify(contacts_list)


def convert_contact_to_dict(contact):
    return {
        "Id": contact.Id,
        "Name": contact.Name,
        # Add other fields here...
    }


if __name__ == '__main__':
    app.run()
