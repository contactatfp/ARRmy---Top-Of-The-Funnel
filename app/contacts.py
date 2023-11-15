import random
from threading import Thread

import faker
import requests
from flask import Blueprint, request, jsonify, render_template
from sqlalchemy import text

from app.models import Contact, Account, Interaction, db
from app.tokens import tokens

DOMAIN = "https://fakepicasso-dev-ed.develop.my.salesforce.com"

contacts_blueprint = Blueprint('contacts', __name__)


@contacts_blueprint.route('/rank_contact/<contact_id>', methods=['GET'])
def rank_contact(contact_id):
    rank_dict = {
        "None": 1,
        "Executive": 2,
        "Manager": 3,
        "Senior Executive": 4,
        "Director": 5,
        "Head": 6,
        "Senior Partner": 7,
        "Vice": 8,  # This will cover all Vice President roles
        "President": 9,
        "COO": 10,
        "CTO": 11,
        "CIO": 12,
        "CSO": 13,
        "CFO": 14,
        "CEO": 15,
        "Chief": 15,  # This will cover all Chief roles
    }

    # Query the specific contact from the database using the contact_id
    contact = Contact.query.get(contact_id)

    if contact is not None:
        job_title = contact.Title if contact.Title else ""  # Use an empty string if JobTitle is None

        # Default rank is 1 if no key phrase exists in the job title
        rank = 1

        for key in rank_dict.keys():
            if key in job_title:
                # Assign the highest rank if the job title contains multiple key phrases
                rank = max(rank, rank_dict[key])

        # Update the contact JobRank field
        contact.JobRank = rank

        # Commit the change to the database
        db.session.commit()
    return rank


@contacts_blueprint.route('/rank_all_contacts', methods=['GET'])
def rank_all_contacts():
    # Your rank dictionary
    rank_dict = {
        "None": 1,
        "Executive": 2,
        "Manager": 3,
        "Senior Executive": 4,
        "Director": 5,
        "Head": 6,
        "Senior Partner": 7,
        "Vice": 8,  # This will cover all Vice President roles
        "President": 9,
        "COO": 10,
        "CTO": 11,
        "CIO": 12,
        "CSO": 13,
        "CFO": 14,
        "CEO": 15,
        "Chief": 15,  # This will cover all Chief roles
    }

    # Fetch all contacts
    all_contacts = Contact.query.all()

    # Loop through each contact and rank them
    for contact in all_contacts:
        job_title = contact.Title if contact.Title else ""  # Use an empty string if Title is None

        # Default rank is 1 if no key phrase exists in the job title
        rank = 1

        for key in rank_dict.keys():
            if key in job_title:
                # Assign the highest rank if the job title contains multiple key phrases
                rank = max(rank, rank_dict[key])

        # Update the contact JobRank field
        contact.JobRank = rank

    # Commit all the changes to the database
    db.session.commit()

    return "All contacts ranked successfully!"


def get_top_5_contacts_using_rank_contact(account_id):
    # Fetch contacts for the given account
    contacts = Contact.query.filter_by(AccountId=account_id).all()

    # If there are no contacts, return an empty list
    if not contacts:
        return []

    # Rank contacts based on the number of interactions
    contacts_with_interactions = db.session.query(Contact, db.func.count(Interaction.id).label('interaction_count')). \
        join(Interaction, Interaction.contactId == Contact.Id). \
        filter(Contact.AccountId == account_id). \
        group_by(Contact.Id). \
        order_by(text('interaction_count DESC')).all()

    top_contacts = []

    # Add contacts with interactions to the top_contacts list
    for contact, _ in contacts_with_interactions:
        top_contacts.append(contact)
        if len(top_contacts) == len(contacts):  # Stop adding if all contacts are added
            break

    # If there are contacts left to add and we haven't reached 5 yet, augment the list with ranked contacts
    if len(top_contacts) < len(contacts):
        # Exclude contacts already in the top_contacts list
        remaining_contacts = [contact for contact in contacts if contact not in top_contacts]

        # Rank the remaining contacts by title
        remaining_contacts.sort(key=lambda x: rank_contact(x.Id), reverse=True)

        # Augment the top_contacts list with the ranked contacts
        top_contacts += remaining_contacts[:5 - len(top_contacts)]

    return top_contacts


@contacts_blueprint.route('/get_contact_for_invite')
def get_contact_for_invite():
    contact_ids = request.args.getlist('contact_ids')
    # split contact_ids by comma
    contact_ids = contact_ids[0].split(',')
    contacts = []
    for contact_id in contact_ids:
        contact = Contact.query.get(contact_id)
        contacts.append(contact)

    contacts_list = [{'Name': contact.Name, 'Id': contact.Id, 'AccountId': contact.AccountId, 'Title': contact.Title}
                     for contact in contacts]
    return jsonify({"contacts": contacts_list})


@contacts_blueprint.route('/company_contacts/<account_id>', methods=['GET'])
def company_contacts(account_id):
    def contact_to_dict(contact):
        # if any of the fields are None, replace with empty string

        return {

            'FirstName': contact.FirstName or 'YOU_DONT_HAVE_A_FIRST_NAME',
            'LastName': contact.LastName or 'YOU_DONT_HAVE_A_LAST_NAME',

            'Email': contact.Email or 'YOU DONT HAVE AN EMAIL ADDRESS',
            'Phone': contact.Phone or 'YOU_DONT_HAVE_A_PHONE_NUMBER',
        }

    contacts = Contact.query.filter_by(AccountId=account_id).all()

    return [contact_to_dict(contact) for contact in contacts]


@contacts_blueprint.route('/get_contacts_for_account/<account_id>', methods=['GET'])
def get_contacts_for_account(account_id):
    contacts = Contact.query.filter_by(AccountId=account_id).all()
    return render_template('contacts_partial.html', contacts=contacts)


@contacts_blueprint.route('/getContacts', methods=['GET'])
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


@contacts_blueprint.route('/contact/<contact_id>')
def contact_details(contact_id):
    from app.prospecting import prospecting_with_contact
    contact = Contact.query.get(contact_id)
    associated_account = Account.query.get(contact.AccountId)
    rec = contact.Recommendation
    if rec is None:
        # make rec a background task
        def background_task():
            # with app.app_context():
            contact.Recommendation = prospecting_with_contact(contact_id)
            db.session.add(contact)
            db.session.commit()

        thread = Thread(target=background_task)
        thread.start()
    return render_template('contact_detail.html', contact=contact, associated_account=associated_account, rec=rec)


def convert_contact_to_dict(contact):
    return {
        "Id": contact.Id,
        "Name": contact.Name,
        # Add other fields here...
    }


@contacts_blueprint.route('/generate_job_titles', methods=['GET', 'POST'])
def add_job_titles():
    fake = faker.Faker()
    # with app.app_context():
    # Fetch all contacts
    contacts = Contact.query.all()
    job_titles = [
        "Chief Executive Officer (CEO)",
        "Chief Technology Officer (CTO)",
        "Chief Information Officer (CIO)",
        "Chief Operating Officer (COO)",
        "Chief Financial Officer (CFO)",
        "Chief Marketing Officer (CMO)",
        "Chief Product Officer (CPO)",
        "Director of Engineering",
        "Director of Product",
        "Director of Information Technology",
        "Director of Marketing",
        "Director of Sales",
        "IT Manager",
        "IT Project Manager",
        "Product Manager",
        "Product Owner",
        "Engineering Manager",
        "Lead Software Engineer",
        "Lead Data Scientist",
        "System Architect",
        "Network Architect",
        "Software Engineer",
        "Front-end Developer",
        "Back-end Developer",
        "Full Stack Developer",
        "Data Scientist",
        "Data Engineer",
        "Machine Learning Engineer",
        "DevOps Engineer",
        "System Administrator",
        "Network Administrator",
        "UX Designer",
        "UI Designer",
        "Graphic Designer",
        "Web Developer",
        "Mobile App Developer",
        "QA Engineer",
        "QA Manager",
        "Business Analyst",
        "Technical Support Specialist",
        "Sales Engineer",
        "Technical Account Manager",
        "Solutions Architect",
        "Cloud Consultant",
        "Cloud Engineer",
        "Database Administrator (DBA)",
        "Security Analyst",
        "Information Security Manager",
        "Head of Research & Development",
        "VP of Engineering"
    ]

    for contact in contacts:
        # Randomly assign a job title from job_titles to the contact
        contact.Title = random.choice(job_titles)

    # Commit the changes to the database
    db.session.commit()

    return jsonify({"success": True})


def fetch_contacts():
    endpoint = '/services/data/v58.0/queryAll/?q=SELECT+name,id,lastName, firstName,AccountId,mailingStreet, phone, email,Salutation,MailingPostalCode,MailingCity,MailingState+from+Contact'
    url = DOMAIN + endpoint

    token = tokens()
    token = token['access_token']

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f"Bearer {token}",
    }
    response = requests.request("GET", url, headers=headers)
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
            Email=record['Email'],

        )

        if Contact.query.filter_by(Id=contact.Id).first() is None:
            db.session.add(contact)

    # Commit the changes
    db.session.commit()

    return contact_data


@contacts_blueprint.route('/contacts', methods=['GET'])
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
    for contact in contacts:
        # check if contact exists in database
        existing_contact = Contact.query.filter_by(Id=contact['Id']).first()
        # If the record doesn't exist, insert it
        if existing_contact is None:
            try:
                db.session.add(contact)
                db.session.commit()
            except Exception as e:
                # Optionally log the error and rollback the transaction
                db.session.rollback()
                print(f"Error inserting contact: {e}")
        else:
            #         update the contact
            existing_contact.AccountId = contact['AccountId']
            existing_contact.LastName = contact['LastName']
            existing_contact.FirstName = contact['FirstName']
            existing_contact.Salutation = contact['Salutation']
            existing_contact.Name = contact['Name']
            existing_contact.MailingStreet = contact['MailingStreet']
            existing_contact.MailingCity = contact['MailingCity']
            existing_contact.MailingState = contact['MailingState']
            existing_contact.MailingPostalCode = contact['MailingPostalCode']
            existing_contact.MailingCountry = contact['MailingCountry']
            existing_contact.Phone = contact['Phone']
            existing_contact.Fax = contact['Fax']
            existing_contact.MobilePhone = contact['MobilePhone']
            existing_contact.Email = contact['Email']
            existing_contact.Title = contact['Title']
            existing_contact.Department = contact['Department']
            existing_contact.AssistantName = contact['AssistantName']

            #         update the database
            try:
                db.session.commit()
            except Exception as e:
                # Optionally log the error and rollback the transaction
                db.session.rollback()
                print(f"Error updating contact: {e}")

    return render_template('contacts.html', contacts=contacts)


@contacts_blueprint.route('/search_contacts')
def search_contacts():
    query = request.args.get('term', '')  # 'term' is commonly used by jQuery UI Autocomplete
    contacts = Contact.query.filter(Contact.Name.ilike(f'%{query}%')).all()  # Simple search by name

    contact_list = [{'label': contact.Name, 'value': contact.Id} for contact in contacts]
    return jsonify(contact_list)


@contacts_blueprint.route('/get_contact_details/<contact_id>')
def get_contact_details(contact_id):
    contact = Contact.query.get(contact_id)
    if contact:
        print(contact.AccountId)
        return jsonify({
            'Name': contact.Name,
            'Phone': contact.Phone,
            'AccountId': contact.AccountId,
            'ContactId': contact.Id,
        })
    else:
        return jsonify({'error': 'Contact not found'}), 404

