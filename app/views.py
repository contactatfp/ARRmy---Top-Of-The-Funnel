from datetime import datetime
from operator import and_

from flask import render_template, redirect, url_for, request, Blueprint
from flask_login import current_user, login_required

import app.tokens
from app.contacts import get_top_5_contacts_using_rank_contact
from app.models import Account, Contact, Interaction, User, RoleEnum, FeedItem, FeedItemType
from app.opps import get_open_opps_value, get_closed_won_opps_total, get_open_opps, get_closed_won_opps
from app.interactions import tier_one_interactions
from app.utils import language_sql

views_blueprint = Blueprint('views', __name__)


@views_blueprint.route('/')
def index():
    # get_data()
    # if user is logged in, redirect to appropriate dashboard
    if current_user.is_authenticated:
        # g.accounts = Account.query.all()
        if current_user.role == RoleEnum.sales_rep:
            return redirect(url_for('views.sales_dashboard'))
        elif current_user.role == RoleEnum.sdr:
            return redirect(url_for('views.dash'))
    return render_template('home.html')


@views_blueprint.route('/dash2', methods=['GET'])
def dash2():
    return render_template('dash2.html')


@views_blueprint.route('/dash', methods=['GET', 'POST'])
def dash():
    days_ago = 365  # default value

    accounts = Account.query.all()
    user = User.query.get(current_user.id)

    focused_accounts = set()

    if request.method == 'POST':
        days_ago = int(request.form.get('time_period', days_ago))

    top5_dict = {}
    contact_count = {}
    total_open = get_open_opps_value(days_ago)
    total_closed = get_closed_won_opps_total(days_ago=365)
    tier1 = tier_one_interactions()
    answer = language_sql()
    test = answer.get_json()
    sql = test['result']

    def days_since_event(event_timestamp):
        if event_timestamp:
            delta = datetime.now() - event_timestamp
            return delta.days
        return None

    # Query latest interactions for all accounts in one go
    latest_calls = {i.account_id: i.timestamp for i in
                    Interaction.query.filter_by(interaction_type="call").order_by(Interaction.timestamp.desc()).all()}
    latest_meetings = {i.account_id: i.timestamp for i in
                       Interaction.query.filter_by(interaction_type="meeting").order_by(
                           Interaction.timestamp.desc()).all()}

    # Query latest opportunities for all accounts in one go
    latest_opps = {}
    for opp in get_open_opps():  # Assuming get_open_opps returns all opportunities
        if opp["node"]["Account"]:
            account_id = opp["node"]["Account"]["Id"]
        else:
            account_id = None
        close_date = datetime.strptime(opp["node"]["CloseDate"]["value"], '%Y-%m-%d')
        if account_id not in latest_opps or close_date > latest_opps[account_id]:
            latest_opps[account_id] = close_date

    for account in accounts:
        top5_contacts = get_top_5_contacts_using_rank_contact(account.Id)
        top5_dict[account.Id] = top5_contacts
        contact_count[account.Id] = len(top5_contacts)
        focus_item = FeedItem.query.filter(
            and_(
                FeedItem.feed_item_type == FeedItemType.focus,
                FeedItem.content.like(f'%{account.Name}%')
            )
        ).first()

        if focus_item:
            focused_accounts.add(account.Id)

    def get_last_call(accountId):
        return days_since_event(latest_calls.get(accountId))

    def get_last_meeting(accountId):
        return days_since_event(latest_meetings.get(accountId))

    def get_last_opp(accountId):
        return days_since_event(latest_opps.get(accountId))

    return render_template('dashboard.html',
                           accounts=accounts,
                           tier1=tier1,
                           user=user,
                           total_closed=total_closed,
                           contact_count=contact_count,
                           total_open=total_open,
                           ask_sql=sql,
                           get_last_meeting=get_last_meeting,
                           get_last_opp=get_last_opp,
                           get_last_call=get_last_call,
                           focused_accounts=focused_accounts
                           )


@views_blueprint.route('/pricing-faq')
def pricing_faq():
    return render_template('pricing-faq.html')


@views_blueprint.route('/sales_dashboard')
@login_required
def sales_dashboard():
    # Check if the logged-in user is a sales representative
    if current_user.role == RoleEnum.sales_rep:
        return render_template('sales_dashboard.html')
    return "Access denied", 403


@views_blueprint.route('/sdr_dashboard', methods=['POST', 'GET'])
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

            contacts = Contact.query.filter_by(AccountId=account_id)

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
                               open_opps_by_account=open_opps_by_account, contacts=contacts)

    return "Access denied", 403


@views_blueprint.route('/reporting', methods=['POST', 'GET'])
def reporting():
    return render_template('reporting.html')


@views_blueprint.route('/get_sales_data')
def get_sales_data():
    from simple_salesforce import Salesforce
    import pandas as pd
    import plotly.express as px
    import json
    from flask import jsonify
    import plotly, requests

    token = app.tokens.get_user_token('contact@fakepicasso.com', 'Lous2balls')
    oauth_token = token['access_token']

    instance_url = token['instance_url']

    graphql_endpoint = f"{instance_url}/services/data/v58.0/graphql"
    headers = {
        "Authorization": f"Bearer {oauth_token}",
        "Content-Type": "application/json"
    }

    query = """query opportunitiesNotClosed {
              uiapi {
                query {
                  Opportunity(
                    where: {
                      not: {
                        or: [
                          { StageName: { eq: "Closed Won" } }
                          { StageName: { eq: "Closed Lost" } }
                        ]
                      }
                    }
                  ) {
                    edges {
                      node {
                        Id
                        Account {  # Add this line
                          Name {  # And this line
                            value
                          }
                        }
                        NextStep {
                          value
                        }
                        CloseDate {
                          value
                          displayValue
                        }
                        Description {
                          value
                        }
                        StageName {
                          value
                        }
                        Amount {
                          value
                        }  
                      }
                    }
                  }
                }
              }
            }
            """

    try:
        response = requests.post(graphql_endpoint, json={'query': query}, headers=headers)
        if response.status_code == 200:
            json_data = response.json()
            # if 'errors' in json_data:
            #     return jsonify({'error': json_data['errors']}), 400

            df = pd.json_normalize(json_data['data']['uiapi']['query']['Opportunity']['edges'])
            fig = px.bar(df, x='node.Account.Name.value', y='node.Amount.value', title='Salesforce Opportunity Data')
            plot_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
            return jsonify({'plot': plot_json})

        else:
            return jsonify({"error": "Failed to fetch data"}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500