import json
import logging
from datetime import timedelta
import pandas as pd
import requests
from dateutil.parser import parse
from faker.generator import random
from flask import Flask, render_template, redirect, url_for, flash, jsonify, abort, render_template_string, g
from flask import request
from flask_apscheduler import APScheduler
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_migrate import Migrate
# import langchain
# from langchain.chains.summarize import load_summarize_chain
from langchain.chat_models import ChatOpenAI
from langchain.tools import Tool
from langchain.utilities import GoogleSearchAPIWrapper
from langchain.utilities import SQLDatabase
from langchain_experimental.sql import SQLDatabaseChain
from sqlalchemy import text
from sqlalchemy.orm import joinedload

import main
from app.forms import EventForm
from app.forms import SignupForm, LoginForm, InvitationForm
from app.models import db, User, RoleEnum, init_db, Account, Contact, Interaction, Event, Address, Invitation, \
    InvitationStatus
from app.prospecting import bio_blueprint
from app.rank_algo import rank_companies
from flask_caching import Cache
import faker

app = Flask(__name__)
app.register_blueprint(bio_blueprint)

cache = Cache(config={'CACHE_TYPE': 'simple'})
cache.init_app(app)


class Config:
    SCHEDULER_API_ENABLED = True


app.config.from_object(Config)

scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

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
SALESFORCE_API_ENDPOINT = "/services/data/v58.0/sobjects/"
SALESFORCE_API_OPPS = "/services/data/v58.0/graphql"


@scheduler.task('interval', id='prospecting_task', days=30, start_date='2023-09-14 20:37:01')
def prospecting():
    from langchain.chat_models import ChatOpenAI
    from langchain.prompts.chat import (
        ChatPromptTemplate,
        SystemMessagePromptTemplate,
        HumanMessagePromptTemplate,
    )
    from app.prospecting import prospecting_overview, prospecting_products, prospecting_market, \
        prospecting_recent_partnerships, prospecting_concerns, prospecting_achievements, prospecting_industry_pain, \
        prospecting_operational_challenges, prospecting_latest_news, prospecting_recent_events, \
        prospecting_customer_feedback

    with app.app_context():
        top_accounts = Account.query.order_by(Account.Score.desc()).limit(2).all()
        for account in top_accounts:
            company_name = account.Name
            overview = prospecting_overview(company_name)
            products = prospecting_products(company_name)
            market = prospecting_market(company_name)
            achievements = prospecting_achievements(company_name)
            industry_pain = prospecting_industry_pain(company_name)
            concerns = prospecting_concerns(company_name)
            operational_challenges = prospecting_operational_challenges(company_name)
            latest_news = prospecting_latest_news(company_name)
            recent_events = prospecting_recent_events(company_name)
            customer_feedback = prospecting_customer_feedback(company_name)
            recent_partnerships = prospecting_recent_partnerships(company_name)

            account.Overview = overview
            account.Products = products
            account.Market = market
            account.Achievements = achievements
            account.Market = market
            account.IndustryPain = industry_pain
            account.Concerns = concerns
            account.OperationalChallenges = operational_challenges
            account.LatestNews = latest_news
            account.RecentEvents = recent_events
            account.CustomerFeedback = customer_feedback
            account.RecentPartnerships = recent_partnerships

            db.session.add(account)
            db.session.commit()

            company_bio = f"{overview} {products} {market} {achievements} {industry_pain} {concerns} {operational_challenges} {latest_news} {recent_events} {customer_feedback} {recent_partnerships}"

            chat = ChatOpenAI(temperature=0, model="gpt-3.5-turbo-16k", openai_api_key=config['openai_api-key'])
            template = (
                "You are a helpful assistant that takes in a customer company bio and converts it to a report for a sales "
                "rep. The sales rep works for a separate company and is trying to sell into the company with the bio. The bio will"
                "have an Overview (including leadership, products, market fit), Challenges, and News. The report should be 1 "
                "paragraph long which will make one recommendation. The recommendation is for the sales rep, who is not from the company bio, on how to proceed to get a meeting "
                "scheduled with the company bio. The focus should be on solving a challenge for the customer. \n\n"
                "Bio: {text}."
            )
            system_message_prompt = SystemMessagePromptTemplate.from_template(template)
            human_template = "{text}"
            human_message_prompt = HumanMessagePromptTemplate.from_template(human_template)

            chat_prompt = ChatPromptTemplate.from_messages(
                [system_message_prompt, human_message_prompt]
            )

            answer = chat(
                chat_prompt.format_prompt(
                    text=company_bio
                ).to_messages()
            )
            print(answer.content)
            account.Recommendations = answer.content
            db.session.add(account)
            db.session.commit()

            # # PROBLEMATIC USING SECTIONS HARDCODED
            # sections = answer.content.split('\n\n')  # Assuming paragraphs are separated by two newlines
            # overview_section = sections[0]
            # challenges_section = sections[1]
            # news_section = sections[2]
            # recommendation_section = sections[3]

            cache_key = f"prospecting_data_{account.Id}"

            data_to_cache = {
                'account': account,
                'overview_section': account.Overview,
                'challenges_section': account.Concerns,
                'news_section': account.RecentEvents,
                'recommendation_section': answer.content
            }

            try:
                cache.set(cache_key, data_to_cache, timeout=24 * 60 * 60)  # Cache for 24 hours
            except Exception as e:
                print(f"Error setting cache: {e}")


# @app.cli.command("prospecting-scheduler")
# def prospecting_command():
#     prospecting()


@scheduler.task('interval', id='do_rank_companies', days=1, start_date='2023-09-14 20:35:01')
def scheduled_rank_companies():
    try:
        with app.app_context():
            ranked_companies = rank_companies()
            for company_id, (score, rank) in ranked_companies.items():
                # search for account by company_id
                company = Account.query.get(company_id)
                if company:  # Check if company exists
                    company.Score = score
                    company.Rank = rank
                    db.session.add(company)
            db.session.commit()
            logging.info("Companies ranked successfully.")
    except Exception as e:
        logging.error(f"Error in scheduled_rank_companies: {e}")


@app.cli.command("rank-companies")
def rank_companies_command():
    scheduled_rank_companies()


@app.route('/rank_contact/<contact_id>', methods=['GET'])
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

        # Default rank is 0 if no key phrase exists in the job title
        rank = 0

        for key in rank_dict.keys():
            if key in job_title:
                # Assign the highest rank if the job title contains multiple key phrases
                rank = max(rank, rank_dict[key])

        # Update the contact JobRank field
        contact.JobRank = rank

        # Commit the change to the database
        db.session.commit()
    return rank


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


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


@app.route('/')
def index():
    get_data()
    # if user is logged in, redirect to appropriate dashboard
    if current_user.is_authenticated:
        # g.accounts = Account.query.all()
        if current_user.role == RoleEnum.sales_rep:
            return redirect(url_for('sales_dashboard'))
        elif current_user.role == RoleEnum.sdr:
            return redirect(url_for('sdr_dashboard'))
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
                get_data()
                # fix later
                return redirect(url_for('sdr_dashboard'))
            else:
                user = User.query.filter_by(username=form.username.data).first()
                login_user(user)
                accounts = Account.query.all()
                # Redirect to appropriate dashboard
                if user.role == RoleEnum.sales_rep:
                    return redirect(url_for('sales_dashboard'))
                elif user.role == RoleEnum.sdr:
                    return redirect(url_for('sdr_dashboard', accounts=accounts))

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


@app.route('/event_list/<account_id>/<event_city>')
def event_list(account_id, event_city):
    account = Account.query.get(account_id)
    addresses = Address.query.filter_by(city=event_city).all()
    events = []

    for address in addresses:
        if address.event:
            events.append(address.event)
    return render_template('event_list.html', events=events, account=account)


def notes_summary(account_id):
    db = SQLDatabase.from_uri("sqlite:///instance/sfdc.db")
    llm = ChatOpenAI(temperature=0, model="gpt-3.5-turbo-16k", verbose=True, openai_api_key=config['openai_api-key'])
    db_chain = SQLDatabaseChain.from_llm(llm, db, verbose=True)
    # account = query account with ID 001Dp00000KBTVRIA5
    account = Account.query.get(account_id)
    summary = db_chain.run(f'''
    Create an account summary that includes Interactions for the account: {account.Name}
    If there are not Interactions for the account then return "No Interactions for this account"
    ''')
    return summary


@app.route('/save_notes', methods=['POST'])
def save_notes():
    account_id = request.form.get('account_id')
    note_text = request.form.get('note_text')

    # Fetch the account using the account_id
    account = Account.query.get(account_id)
    if not account:
        return jsonify(status="error", message="Account not found"), 404

    # Update the Notes field
    account.Notes = note_text
    db.session.commit()

    return jsonify(status="success", message="Notes updated successfully")


@app.route('/tier', methods=['GET'])
def get_tier():
    account_id = request.args.get('id')
    account = Account.query.get(account_id)

    # get all opportunities for account that closed won in last 12 months
    closed_won_opps = get_closed_won_opps()

    # sort all opps for this for close in the last 12 months
    closed_won_opps = list(filter(
        lambda opp: datetime.strptime(opp["node"]["CloseDate"]["value"], '%Y-%m-%d') > datetime.now() - timedelta(
            days=365), closed_won_opps))
    closed_won_opps = list(filter(lambda opp: opp["node"]["Account"]["Id"] == account_id, closed_won_opps))

    # get all opportunities for account that are open
    open_opps = get_open_opps()
    open_opps = list(filter(lambda opp: opp["node"]["Account"]["Id"] == account_id, open_opps))

    # sort all opps for this for close in the next 6 months
    open_opps = list(filter(
        lambda opp: datetime.strptime(opp["node"]["CloseDate"]["value"], '%Y-%m-%d') < datetime.now() + timedelta(
            days=180), open_opps))

    # Format the data
    formatted_data = f"<strong>Rank:</strong> {account.Rank if account else 'N/A'}<br>"
    formatted_data += f"<strong>Closed Won Opportunities:</strong> {len(closed_won_opps)}<br>"
    formatted_data += f"<strong>Open Opportunities:</strong> {len(open_opps)}<br>"
    total_won = 0
    for opp in closed_won_opps:
        formatted_data += f"<span class='closed-won-opp'><strong>Closed Won Opp:</strong> Closed on {opp['node']['CloseDate']['value']}</span><br>"
        if len(closed_won_opps) > 0:
            total_won += opp["node"]["Amount"]["value"]
    if total_won > 0:
        total_won = int(total_won)
        formatted_data += f"<span class='closed-won-opp'><br><strong>Total Closed in Last 12: $</strong>{total_won}</span><br>"

    for opp in open_opps:
        formatted_data += f"<span class='open-opp'><strong>Open Opp:</strong> Should close on {opp['node']['CloseDate']['value']}</span><br>"

    return formatted_data


@app.route('/sdr_dashboard', methods=['POST', 'GET'])
# @login_required
def sdr_dashboard():
    # Check if the logged-in user is an SDR
    if current_user.role == RoleEnum.sdr:

        accounts = Account.query.all()

        events = []

        # Initialize an empty dictionary to store the number of events for each account
        account_event_counts = {}

        top5_dict = {}
        color_dict = {}
        closed_opps = get_closed_won_opps()
        open_opps = get_open_opps()

        # Organize opportunities by account.Id and return count for opp in each account
        # FIX 1: This is not working as expected. It is returning the same count for each account
        open_opps_by_account = {opp["node"]["Account"]["Id"]: +1 for opp in open_opps}
        closed_opps_by_account = {opp["node"]["Account"]["Id"]: +1 for opp in closed_opps}

        #

        # Determine color for each account based on opp status
        for account in accounts:
            top5_dict[account.Id] = get_top_5_contacts_using_rank_contact(account.Id)
            account_id = account.Id

            if account_id in open_opps_by_account:
                color_dict[account_id] = "Green"
            elif account_id in closed_opps_by_account:
                color_dict[account_id] = "Yellow"
            else:
                color_dict[account_id] = "Red"

        def get_last_interaction(accountId):
            interaction = Interaction.query.filter_by(account_id=accountId).order_by(
                Interaction.timestamp.desc()).first()
            return interaction

        return render_template('sdr_dashboard.html', accounts=accounts, get_last_interaction=get_last_interaction,
                               account_event_counts=account_event_counts, events=events, top5=top5_dict,
                               status_color=color_dict, closed_opps_by_account=closed_opps_by_account,
                               open_opps_by_account=open_opps_by_account)

    return "Access denied", 403


from datetime import datetime


@app.route('/events_page')
def events_page():
    # Retrieve all events from the database
    # with app.context
    with app.app_context():
        events = Event.query.options(joinedload(Event.location)).all()

    # Render the events page and pass the events to the template
    return render_template('events_page.html', events=events)


@app.route('/add_event', methods=['GET', 'POST'])
def add_event():
    form = EventForm()
    if request.method == 'POST':
        # Add new event to the database here
        # Then redirect to the events page or some other page
        data = request.form

        # Extract data fields

        start_time_str = data.get('start_time')
        end_time_str = data.get('end_time')

        # Convert the date strings to datetime objects
        start_time = datetime.strptime(start_time_str, "%Y-%m-%dT%H:%M")
        end_time = datetime.strptime(end_time_str, "%Y-%m-%dT%H:%M")

        street, city, state, country = parse_location(form.location.data)
        address = Address(
            street=street,
            city=city,
            state=state,
            country=country
        )
        # db.session.add(address)
        # db.session.commit()

        event = Event(
            name=form.name.data,
            description=form.description.data,
            start_time=start_time,
            end_time=end_time,
            audience=form.audience.data,
            event_type=form.event_type.data,
            location=address,
            cost=form.cost.data,
            created_by=current_user.id,
            created_at=datetime.now(),
            sponsor=form.sponsor.data,
            expected_attendees=form.expected_attendees.data,
            actual_attendees=form.actual_attendees.data,
            marketing_channel=form.marketing_channel.data
        )
        db.session.add(event)
        db.session.commit()
        return redirect(url_for('events_page'))
    return render_template('add_event.html', form=form)


def parse_location(location_string):
    print(f"Trying to parse: {location_string}")  # Add this line
    components = location_string.split(',')

    # Check if we have all the required components
    if len(components) != 4:
        raise ValueError("Invalid location string provided.")

    street = components[0].strip()
    city = components[1].strip()
    state = components[2].strip()
    country = components[3].strip()

    return street, city, state, country


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


def get_distance(loc1, loc2):
    # Define the base URL for the Distance Matrix API
    base_url = "https://maps.googleapis.com/maps/api/distancematrix/json"

    # Define the parameters for the GET request
    params = {
        "origins": f"{loc1[0]},{loc1[1]}",
        "destinations": f"{loc2[0]},{loc2[1]}",
        "units": "imperial",
        "key": config['google-maps-api'],
    }

    # Send the GET request
    response = requests.get(base_url, params=params)

    # Convert the response to JSON
    data = response.json()

    # Extract the distance from the JSON response
    distance = data["rows"][0]["elements"][0]["distance"]["text"]

    # Remove " mi" from the end of the distance string and convert it to a float
    distance = float(distance[:-3])

    return distance


@app.route('/events_in_area', methods=['GET'])
def get_events_in_area():
    # Get the optional miles_from_event parameter
    miles_from_event = request.args.get('miles_from_event', default=0, type=int)

    # Get the list of accounts from the database
    accounts = Account.query.all()

    # This will store the final list of events
    events_in_area = []

    # Iterate over each account
    for account in accounts:
        # Get the corresponding address based on the city
        address = Address.query.filter_by(city=account.BillingCity).first()

        # If the address exists and the event exists
        if address and address.event:
            # If miles_from_event is specified, check the distance
            if miles_from_event > 0:
                distance = get_distance((account.BillingLatitude, account.BillingLongitude),
                                        (address.event.location.latitude, address.event.location.longitude))

                # If the event is within the specified range, add it to the list
                if distance <= miles_from_event:
                    events_in_area.append(address.event)
            else:
                # If miles_from_event is not specified, simply add the event to the list
                events_in_area.append(address.event)

    # Convert the list of events to JSON and return it
    return jsonify([event.to_dict() for event in events_in_area])


@app.route('/invitation/create/<account_id>/<event_id>', methods=['GET', 'POST'])
def create_invitation(account_id, event_id):
    form = InvitationForm()

    # Fetch the account
    account = Account.query.get_or_404(account_id)

    # Fetch the event
    event = Event.query.get_or_404(event_id)

    contacts = Contact.query.filter_by(AccountId=account.Id).all()
    form.contact_id.choices = [(contact.Id, contact.Name) for contact in contacts]

    if form.validate_on_submit():
        invitation = Invitation(event_id=form.event_id.data,
                                contact_id=form.contact_id.data,
                                account_id=form.account_id.data,
                                contact_title=form.contact_title.data,
                                status=InvitationStatus[form.status.data])
        db.session.add(invitation)
        db.session.commit()
        flash('Invitation created successfully', 'success')
        return redirect(url_for('invitation_list'))

    return render_template('create_invitation.html', title='Create Invitation', form=form, contacts=contacts,
                           event=event)


@app.route('/account/<string:account_id>', methods=['GET'])
def account_details(account_id):
    account = Account.query.get(account_id)
    if account is None:
        abort(404, description="Account not found")
    cache_key = f"prospecting_data_{account_id}"
    prospecting_data = cache.get(cache_key)

    if prospecting_data:
        # Pass the cached data to the template
        return render_template('account_details.html', account=account, prospecting_data=prospecting_data)
    else:
        return render_template('account_details.html', account=account)

    # return render_template(
    #     'prospecting.html',
    #     account=account,
    #     overview_section=overview_section,
    #     challenges_section=challenges_section,
    #     news_section=news_section,
    #     recommendation_section=recommendation_section
    #         )


def time_since_last_interaction(last_interaction_timestamp):
    now = datetime.now()
    difference = now - last_interaction_timestamp
    days_difference = difference.days

    if days_difference == 0:
        return 'Today'
    elif days_difference == 1:
        return 'Yesterday'
    elif days_difference < 7:
        return f'{days_difference} days ago'
    elif days_difference < 30:
        weeks_difference = days_difference // 7
        return f'{weeks_difference} weeks ago'
    else:
        months_difference = days_difference // 30
        return f'{months_difference} months ago'


app.jinja_env.filters['time_since'] = time_since_last_interaction


@app.route('/get_interactions', methods=['GET'])
def get_interactions():
    account_id = request.args.get('account_id')
    interactions = Interaction.query.filter_by(account_id=account_id).all()
    interactions_data = [{"type": interaction.interaction_type, "description": interaction.description,
                          "timestamp": interaction.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                          "user_id": interaction.user_id} for interaction in interactions]
    return jsonify(interactions_data)


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


@app.route('/get_data', methods=['GET'])
@login_required
def get_data():
    token = tokens()
    if not token:
        return {"error": "Failed to get Salesforce token"}

    for model, api_endpoint in [(Account, "account"), (Contact, "contact"), (Interaction, "interaction"),
                                (Event, "event"), (Address, "address")]:
        url = f"{DOMAIN}/services/data/v58.0/queryAll/?q=SELECT+name,id+from+{api_endpoint}"
        response = create_api_request("GET", url, token['access_token'])
        process_response(response, model)

    return jsonify({"success": True})


@app.route('/add_account', methods=['POST'])
@login_required
def add_account():
    data = request.json
    url = f"{DOMAIN}{SALESFORCE_API_ENDPOINT}account"

    token = tokens()
    if not token:
        return {"error": "Failed to get Salesforce token"}

    # Map input data to Salesforce fields
    sf_data = {
        "Name": data.get('name'),
        "BillingStreet": data.get('street'),
        "BillingCity": data.get('city'),
        "BillingState": data.get('state'),
        "BillingPostalCode": data.get('zip')
    }

    response = create_api_request("POST", url, token['access_token'], sf_data)
    if response.status_code == 201:
        get_data()
        return jsonify({"success": True})
    else:
        logging.error(f"Error adding account: {response.text}")
        return jsonify({"success": False, "error": response.text})


def soql_query(query):
    # Make sure the query is properly formatted without the '+' characters
    soql_query = query.replace('+', ' ')
    return soql_query


@app.route('/company_contacts/<account_id>', methods=['GET'])
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


@app.route('/last30')
def last30():
    account_id = request.args.get('id')
    count = Interaction.query.filter_by(account_id=account_id).count()
    if count == 0:
        last_interaction_date = 'No Interactions'
    else:
        last_interaction_date = Interaction.query.filter_by(account_id=account_id).order_by(
            Interaction.timestamp.desc()).first().timestamp

    # Define the tooltip's HTML structure
    tooltip_content = """
    <div>
        <strong>Last 30-day Interactions:</strong>
        <span>{{ count }}</span>
        <br>
        <strong>Last Interaction Date:</strong>
        <span>{{ last_interaction_date }}</span>
        
    </div>
    """

    # Render and return the tooltip content
    return render_template_string(tooltip_content, count=count, last_interaction_date=last_interaction_date)


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


@app.route('/contact/<contact_id>')
def contact_details(contact_id):
    contact = Contact.query.get(contact_id)
    associated_account = Account.query.get(contact.AccountId)  # Assuming you have an Account model
    return render_template('contact_detail.html', contact=contact, associated_account=associated_account)


def convert_contact_to_dict(contact):
    return {
        "Id": contact.Id,
        "Name": contact.Name,
        # Add other fields here...
    }


@app.route('/upload', methods=['GET', 'POST'])
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


@app.route('/uploadInteractions', methods=['GET', 'POST'])
@login_required
def generate_interaction_data():
    num_rows = request.args.get('num_rows', default=100, type=int)

    from faker import Faker
    fake = Faker()
    data = []

    # Possible descriptions for the interactions
    descriptions = ['Great call with', 'Follow-up with', 'Introductory call with', 'Closing call with', 'Check-in with']
    account_ids = [account.Id for account in Account.query.all()]
    contact_ids = [contact.Id for contact in Contact.query.all()]
    for _ in range(num_rows):
        timestamp = fake.date_time_between(start_date='-1y', end_date='now')  # random date in the last year
        description = random.choice(descriptions) + ' ' + fake.name()

        row = {
            'interaction_type': 'call',
            'description': description,
            'timestamp': timestamp,
            'account_id': random.choice(account_ids),
            'user_id': current_user.id,
            'contactId': random.choice(contact_ids)
        }
        data.append(row)

        #     add to database
        interaction = Interaction(
            interaction_type=row['interaction_type'],
            description=row['description'],
            timestamp=row['timestamp'],
            account_id=row['account_id'],
            user_id=row['user_id'],
            contactId=row['contactId']
        )
        db.session.add(interaction)
        db.session.commit()

    return jsonify(data)


@app.route('/uploadEvents', methods=['GET', 'POST'])
@login_required
def generate_event_data():
    num_rows = request.args.get('num_rows', default=100, type=int)

    from faker import Faker
    fake = Faker()
    data = []

    # Possible event types
    event_types = ['Conference', 'Webinar', 'Meetup', 'Workshop', 'Seminar']

    # Fetch unique BillingCity values from Account model
    billing_cities = list(set(account.BillingCity for account in Account.query.all()))

    for _ in range(num_rows):
        start_time = fake.date_time_between(start_date='-1y', end_date='now')  # random date in the last year
        end_time = fake.date_time_between(start_date=start_time, end_date='+30d')  # random date after start time
        description = fake.sentence(nb_words=10)
        name = fake.catch_phrase()

        row = {
            'name': name,
            'description': description,
            'start_time': start_time,
            'end_time': end_time,
            'created_by': current_user.id,
            'audience': fake.catch_phrase(),
            'event_type': random.choice(event_types),
            'cost': fake.random_int(min=0, max=1000),
            'sponsor': fake.company(),
            'expected_attendees': fake.random_int(min=0, max=500),
            'actual_attendees': fake.random_int(min=0, max=500),
            'marketing_channel': fake.catch_phrase(),
            'location': {
                'city': random.choice(billing_cities),  # Randomly pick a city from the list
                'country': fake.country(),
                'state': fake.state(),
                'zip_code': fake.zipcode(),
                'street': fake.street_address()
            }
        }
        data.append(row)

        #     add to database
        location = Address(**row['location'])  # Create Address object
        db.session.add(location)
        db.session.flush()  # This is needed to generate id for new Address

        event = Event(
            name=row['name'],
            description=row['description'],
            start_time=row['start_time'],
            end_time=row['end_time'],
            created_by=row['created_by'],
            audience=row['audience'],
            event_type=row['event_type'],
            cost=row['cost'],
            sponsor=row['sponsor'],
            expected_attendees=row['expected_attendees'],
            actual_attendees=row['actual_attendees'],
            marketing_channel=row['marketing_channel'],
            location=location  # Set location to the Address object
        )
        db.session.add(event)
        db.session.commit()

    return jsonify(data)


@app.route('/generate_job_titles', methods=['GET', 'POST'])
def add_job_titles():
    fake = faker.Faker()
    with app.app_context():
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


@app.route('/news', methods=['GET', 'POST'])
@login_required
def news():
    # get company name from request
    company_name = request.args.get('company', default='', type=str)

    import os

    os.environ["GOOGLE_CSE_ID"] = config['GOOGLE_CSE_ID']
    os.environ["GOOGLE_API_KEY"] = config['GOOGLE_API_KEY']

    search = GoogleSearchAPIWrapper()

    def top5_results(query):
        return search.results(query, 5)

    tool = Tool(
        name="Google Search Snippets",
        description="Search Google for recent results.",
        func=top5_results,
    )
    answer = tool.run("Company News for: " + company_name)

    formatted_response = ""
    for item in answer:
        formatted_response += f'<p><a href="{item["link"]}">{item["title"]}</a><br>{item["snippet"]}</p>'

    return formatted_response


# @app.route('/salesforce/opps', methods=['GET', 'POST'])
# def get_opps_for_account():
#     url = f"{DOMAIN}{SALESFORCE_API_OPPS}"
#     token = tokens()
#     if not token:
#         return {"error": "Failed to get Salesforce token"}
#
#     query = """
#     query opportunitiesNotClosed {
#       uiapi {
#         query {
#           Opportunity(
#             where: {
#               not: {
#                 or: [
#                   { StageName: { eq: "Closed Won" } }
#                   { StageName: { eq: "Closed Lost" } }
#                 ]
#               }
#             }
#           ) {
#             edges {
#               node {
#                 Id
#                 Account {
#                   Name {
#                     value
#                   }
#                   Id
#                 }
#                 NextStep {
#                   value
#                 }
#                 CloseDate {
#                   value
#                   displayValue
#                 }
#                 Description {
#                   value
#                 }
#                 StageName {
#                   value
#                 }
#               }
#             }
#           }
#         }
#       }
#     }
#     """
#
#     # Prepare the payload as a Python dictionary
#     payload = {"query": query, "variables": {}}
#
#     # Update the request to send JSON data
#     response = create_api_request("POST", url, token['access_token'], payload)
#     response_json = response.json()
#     opportunities = response_json["data"]["uiapi"]["query"]["Opportunity"]["edges"]
#
#     # Loop through each opportunity and print the desired information
#     for opp in opportunities:
#         account_name = opp["node"]["Account"]["Name"]["value"]
#         close_date = opp["node"]["CloseDate"]["value"]
#         stage_name = opp["node"]["StageName"]["value"]
#         print(f"Account Name: {account_name}, Close Date: {close_date}, Stage Name: {stage_name}")
#
#     return render_template('opportunities.html', opportunities=opportunities)


@app.route('/salesforce/account-status/<account_id>', methods=['GET'])
def get_account_status(account_id):
    url = f"{DOMAIN}{SALESFORCE_API_OPPS}"
    token = tokens()
    if not token:
        return {"error": "Failed to get Salesforce token"}

    # Check for open opportunities
    open_query = f"""
    query openOpportunitiesForAccount {{
      uiapi {{
        query {{
          Opportunity(
            where: {{
              and: [
                {{ Account: {{ Id: {{ eq: "{account_id}" }} }} }},
                {{ StageName: {{ eq: "Open" }} }}
              ]
            }}
          ) {{
            edges {{
              node {{
                Id
              }}
            }}
          }}
        }}
      }}
    }}
    """
    open_payload = {"query": open_query, "variables": {}}
    response_open = create_api_request("POST", url, token['access_token'], open_payload)
    open_count = len(response_open.json()["data"]["uiapi"]["query"]["Opportunity"]["edges"])

    # Check for closed opportunities within the last 12 months
    twelve_months_ago = (datetime.now() - timedelta(days=365)).isoformat()
    closed_query = f"""
    query recentClosedOpportunitiesForAccount {{
      uiapi {{
        query {{
          Opportunity(
            where: {{
              and: [
                {{ Account: {{ Id: {{ eq: "{account_id}" }} }} }},
                {{ CloseDate: {{ gte: "{twelve_months_ago}" }} }},
                {{ or: [
                  {{ StageName: {{ eq: "Closed Won" }} }},
                  {{ StageName: {{ eq: "Closed Lost" }} }}
                ]}}
              ]
            }}
          ) {{
            edges {{
              node {{
                Id
              }}
            }}
          }}
        }}
      }}
    }}
    """
    closed_payload = {"query": closed_query, "variables": {}}
    response_closed = create_api_request("POST", url, token['access_token'], closed_payload)
    test = response_closed.json()
    # closed_count = len(response_closed.json()["data"]["uiapi"]["query"]["Opportunity"]["edges"])

    # closed_count = len(response_closed.json()["data"]["uiapi"]["query"]["Opportunity"]["edges"])

    # Determine color based on counts
    if open_count > 0:
        status_color = "Green"
    # elif closed_count > 0:
    #     status_color = "Yellow"
    else:
        status_color = "Red"

    return status_color


@app.route('/won', methods=['GET', 'POST'])
def get_closed_won_opps(days_ago=365):
    url = "https://fakepicasso-dev-ed.develop.my.salesforce.com/services/data/v58.0/graphql"
    payload = "{\"query\":\"query opportunitiesClosedWon {\\n  uiapi {\\n    query {\\n      Opportunity(\\n        where: {\\n          StageName: { eq: \\\"Closed Won\\\" }\\n        }\\n      ) {\\n        edges {\\n          node {\\n            Id\\n            Account {\\n              Name {\\n                value\\n              }\\n              Id \\n            }\\n            CloseDate {\\n              value\\n            }\\n            StageName {\\n              value\\n            }\\n            Amount {\\n              value\\n            }\\n          }\\n        }\\n      }\\n    }\\n  }\\n}\\n\",\"variables\":{}}"
    token = tokens()
    if not token:
        return {"error": "Failed to get Salesforce token"}
    else:
        token = token['access_token']
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}',
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    response_json = response.json()
    opportunities = response_json["data"]["uiapi"]["query"]["Opportunity"]["edges"]
    # filter opps won in the last 12 months, keep in mind the CloseDate is a string and provide count
    opportunities = [opportunity for opportunity in opportunities if
                     datetime.strptime(opportunity["node"]["CloseDate"]["value"], "%Y-%m-%d") > (
                             datetime.now() - timedelta(days=days_ago))]

    return opportunities


@app.route('/open', methods=['GET', 'POST'])
def get_open_opps(days_ago=365):
    url = "https://fakepicasso-dev-ed.develop.my.salesforce.com/services/data/v58.0/graphql"
    payload = "{\"query\":\"query opportunitiesNotClosed {\\n  uiapi {\\n    query {\\n      Opportunity(\\n        where: {\\n          not: {\\n            or: [\\n              { StageName: { eq: \\\"Closed Won\\\" } }\\n              { StageName: { eq: \\\"Closed Lost\\\" } }\\n            ]\\n          }\\n        }\\n      ) {\\n        edges {\\n          node {\\n            Id\\n            Account {  # Add this line\\n              Name {  # And this line\\n                value\\n              }\\n              Id\\n            }\\n            # NextStep {\\n            #   value\\n            # }\\n            CloseDate {\\n              value\\n            #   displayValue\\n            }\\n            # Description {\\n            #   value\\n            # }\\n            StageName {\\n              value\\n            }\\n          }\\n        }\\n      }\\n    }\\n  }\\n}\\n\",\"variables\":{}}"
    token = tokens()
    if not token:
        return {"error": "Failed to get Salesforce token"}
    else:
        token = token['access_token']
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}',
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    response_json = response.json()
    opportunities = response_json["data"]["uiapi"]["query"]["Opportunity"]["edges"]
    # filter opps won in the last 12 months, keep in mind the CloseDate is a string and provide count
    # opportunities = [opportunity for opportunity in opportunities if
    #                  datetime.strptime(opportunity["node"]["CloseDate"]["value"], "%Y-%m-%d") > (
    #                          datetime.now() - timedelta(days=days_ago))]

    return opportunities


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


def parse_dates(record, date_fields):
    """
    Function to parse date fields in a record.
    """
    for key, value in record.items():
        if key in date_fields and value is not None:
            record[key] = parse(value)

    return record


@app.route('/data', methods=['GET', 'POST'])
def data():
    contact = main.contacts()
    events = main.generate_event_data()
    interactions = main.generate_interaction_data()
    jobs = main.add_job_titles()

    rank = main.scheduled_rank_companies()
    prospect = main.prospecting()

    return redirect(url_for('sdr_dashboard'))


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


if __name__ == '__main__':
    app.run()
