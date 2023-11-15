import json
import logging
from datetime import datetime

import pandas as pd
import requests
from flask_caching import Cache
from flask_login import login_required, current_user
from dateutil.parser import parse

# from app.background_process import scheduled_rank_companies
from app.models import db, Account, Interaction
from app.tokens import tokens
from flask import request, jsonify, Blueprint, redirect, url_for
import os


DOMAIN = "https://fakepicasso-dev-ed.develop.my.salesforce.com"
SALESFORCE_API_ENDPOINT = "/services/data/v58.0/sobjects/"
SALESFORCE_API_OPPS = "/services/data/v58.0/graphql"

openai_api_key = os.getenv("OPENAI_API_KEY")

cache = Cache(config={'CACHE_TYPE': 'simple'})

util_blueprint = Blueprint('util', __name__)


def create_api_request(method, url, token, data=None):
    """
    Function to create and send an API request.
    """
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}',
    }
    response = requests.request(method, url, headers=headers, data=json.dumps(data))

    return response


@util_blueprint.route('/ask_sql', methods=['GET', 'POST'])
def language_sql():
    from langchain.utilities import SQLDatabase
    from langchain.chat_models import ChatOpenAI
    from langchain_experimental.sql import SQLDatabaseChain

    # get input from the request
    query = request.args.get('query', default='How many accounts have a score over 50 total?', type=str)
    db = SQLDatabase.from_uri("sqlite:///instance/sfdc.db")
    llm = ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo-16k", verbose=True,
                     openai_api_key=openai_api_key)
    db_chain = SQLDatabaseChain.from_llm(llm, db, verbose=True)

    answer = db_chain.run(query)

    return jsonify({"result": answer})


def process_dataframe(df, model, api_url, token):
    """
    Function to process a dataframe and upload records to the API and local database.
    """
    for _, row in df.iterrows():
        response = create_api_request("POST", api_url, token, data=row.to_dict())
        if response.status_code == 201:
            try:
                db.session.add(model(**row.to_dict()))
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                logging.error(f"Error inserting record: {e}")
        else:
            logging.error(f"Error adding record to API: {response.text}")


def process_response(response, model):
    """
    Function to process API response and save records to the database.
    """
    if response.status_code == 200:
        data = response.json()
        records = data.get('records', [])
        for record in records:
            record = parse_dates(record, ['CreatedDate', 'SLAExpirationDate__c', 'LastModifiedDate', 'LastViewedDate',
                                          'LastReferencedDate'])
            obj = model.query.filter_by(Id=record['Id']).first()
            if obj is None:
                # drop record['attributes'] as it is not a column in the database
                record.pop('attributes', None)
                try:
                    db.session.add(model(**record))
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    logging.error(f"Error inserting record: {e}")
            else:
                for key, value in record.items():
                    setattr(obj, key, value)
                try:
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    logging.error(f"Error updating record: {e}")

        return {'record_size': len(records), 'records': records}
    else:
        logging.error(f"Unexpected response from API: {response.text}")
        return {"error": "Unexpected response from API"}


def parse_dates(record, date_fields):
    """
    Function to parse date fields in a record.
    """
    for key, value in record.items():
        if key in date_fields and value is not None:
            record[key] = parse(value)

    return record


def to_dict(self):
    return {
        'id': self.id,
        'name': self.name,
        'description': self.description,
        'start_time': self.start_time,
        'end_time': self.end_time,
        'location': {
            'street': self.location.street,
            'city': self.location.city,
            'state': self.location.state,
            'country': self.location.country
        },
        'cost': self.cost,
        'created_at': self.created_at,
        'created_by': self.created_by,
        'audience': self.audience,
        'event_type': self.event_type,
        'sponsor': self.sponsor,
        'expected_attendees': self.expected_attendees,
        'actual_attendees': self.actual_attendees,
        'marketing_channel': self.marketing_channel
    }


@util_blueprint.route('/data', methods=['GET', 'POST'])
def data():
    from app.accounts import add_account_billing_address, add_account_industry, add_account_notes
    from app.contacts import contacts, add_job_titles
    from app. interactions import generate_interaction_data

    contacts()
    # generate_event_data()
    generate_interaction_data()
    add_job_titles()
    add_account_billing_address()
    add_account_industry()
    add_account_notes()
    # scheduled_rank_companies()
    # prospecting()

    return redirect(url_for('views.dash'))


def soql_query(query):
    # Make sure the query is properly formatted without the '+' characters
    soql_query = query.replace('+', ' ')
    return soql_query

def id2Name(id):
    account = Account.query.filter_by(Id=id).first()
    return account.Name


@util_blueprint.route('/logACall', methods=['POST'])
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


@util_blueprint.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    filepath = 'data.csv'
    df = pd.read_csv(filepath)
    df = df.fillna("")
    # Get token once outside the loop
    token = tokens()['access_token']
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }

    for _, row in df.iterrows():
        # Check if the account exists
        account = Account.query.filter_by(Name=row['Company Name']).first()

        # If not, create a new account
        if account is None:
            # account = Account(
            #     Name=row['Company Name'],
            #     BillingStreet=row['Company Street Address'],
            #     BillingCity=row['Company City'],
            #     BillingState=row['Company State'],
            #     BillingPostalCode=row['Company Zip Code'],
            #     BillingCountry=row['Company Country'],
            #     Phone=row['Company HQ Phone'],
            #     Website=row['Website'],
            #     Industry=row['Primary Industry'],
            #     Description=row['All Sub-Industries'],
            #     OwnerId=current_user.id,
            #     CreatedDate=datetime.now(),
            #     LastModifiedDate=datetime.now(),
            #     LastModifiedById=current_user.id,
            #     SystemModstamp=datetime.now()
            # )
            # db.session.add(account)
            # # db.session.commit()

            # Send data to Salesforce
            url = "https://fakepicasso-dev-ed.develop.my.salesforce.com/services/data/v58.0/sobjects/account"
            payload = json.dumps({
                "Name": row['Company Name'],
                "BillingStreet": row['Company Street Address'],
                "BillingCity": row['Company City'],
                "BillingState": row['Company State'],
                "BillingPostalCode": row['Company Zip Code'],
                "BillingCountry": row['Company Country'],
                "Phone": row['Company HQ Phone'],
                "Website": row['Website'],
                "Industry": row['Primary Industry'],
                "Description": row['All Sub-Industries'],
                "OwnerId": current_user.id

            })

            response = requests.post(url, headers=headers, data=payload)
            newAccountURL = f"https://fakepicasso-dev-ed.develop.my.salesforce.com/services/data/v58.0/query/?q=SELECT+Id+FROM+Account+WHERE+Name='{row['Company Name']}'"
            response = requests.get(newAccountURL, headers=headers)
            response_data = response.json()
            account = response_data['records'][0]['Id']

        # # Create a new contact linked to the account
        # contact = Contact(
        #     AccountId=account.Id,  # Use the account.Id instead of 'ZoomInfo Company ID'
        #     LastName=row['Last Name'],
        #     FirstName=row['First Name'],
        #     Name=row['First Name'] + ' ' + row['Last Name'],
        #     Phone=row['Mobile phone'],
        #     Title=row['Job Title'],
        #     Email=row['Email Address']
        # )
        # if Contact.query.filter_by(Id=contact.Id).first() is None:
        #     db.session.add(contact)

        # Send contact data to Salesforce
        url = "https://fakepicasso-dev-ed.develop.my.salesforce.com/services/data/v58.0/sobjects/contact"
        if Account.query.filter_by(Name=row['Company Name']).first() is not None:
            payload = json.dumps({
                "AccountId": account.Id,
                "LastName": row['Last Name'],
                "FirstName": row['First Name'],
                "Title": row['Job Title'],
                "Email": row['Email Address'],

            })
            response = requests.post(url, headers=headers, data=payload)
        else:
            payload = json.dumps({
                "AccountId": account,
                "LastName": row['Last Name'],
                "FirstName": row['First Name'],
                "Title": row['Job Title'],
                "Email": row['Email Address'],
            })
            response = requests.post(url, headers=headers, data=payload)
    # db.session.commit()
    return jsonify({"success": True})
