import random
from datetime import datetime, timedelta

from flask import Blueprint, render_template, request, jsonify, render_template_string, redirect
from flask_login import current_user, login_required

from app.models import Account, Contact, Interaction, db

interactions_blueprint = Blueprint('interactions', __name__, template_folder='templates')

# def time_since_last_interaction(last_interaction_timestamp):
#     now = datetime.now()
#     difference = now - last_interaction_timestamp
#     days_difference = difference.days
#
#     if days_difference == 0:
#         return 'Today'
#     elif days_difference == 1:
#         return 'Yesterday'
#     elif days_difference < 7:
#         return f'{days_difference} days ago'
#     elif days_difference < 30:
#         weeks_difference = days_difference // 7
#         return f'{weeks_difference} weeks ago'
#     else:
#         months_difference = days_difference // 30
#         return f'{months_difference} months ago'

# interactions_blueprint.jinja_env.filters['time_since'] = time_since_last_interaction


@interactions_blueprint.route('/get_interactions', methods=['GET'])
def get_interactions(account_id):
    # account_id = request.args.get('account_id')
    interactions = Interaction.query.filter_by(account_id=account_id).all()
    interactions_data = [{"type": interaction.interaction_type, "description": interaction.description,
                          "timestamp": interaction.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                          "user_id": interaction.user_id} for interaction in interactions]
    return jsonify(interactions_data)


@interactions_blueprint.route('/interaction_details/<int:interaction_id>')
def interaction_details(interaction_id):
    interaction = Interaction.query.get_or_404(interaction_id)
    account = Account.query.get(interaction.account_id)
    contact = Contact.query.get(interaction.contactId)
    return render_template('interaction_details.html', interaction=interaction, account=account, contact=contact,
                           interaction_id=interaction_id)


@interactions_blueprint.route('/uploadInteractions', methods=['GET', 'POST'])
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
    inter_type = ['call', 'email', 'meeting']
    for _ in range(num_rows):
        timestamp = fake.date_time_between(start_date='-1y', end_date='now')  # random date in the last year
        description = random.choice(descriptions) + ' ' + fake.name()

        row = {
            'interaction_type': inter_type[random.randint(0, 2)],
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


@interactions_blueprint.route('/tier1_interactions', methods=['GET', 'POST'])
def tier_one_interactions(timeframe=365):
    # with app.app_context():
        # list out all interactions with an account.Score > 70 and interaction happened with timeframe days ago
        # interactions = Interaction.query.join(Account).filter(Account.Score > 74).all()
    interactions = Interaction.query.join(Account).filter(
            Interaction.timestamp > (datetime.now() - timedelta(days=timeframe)),
            Account.Score > 70).all()
    return len(interactions)


@interactions_blueprint.route('/last30')
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


@interactions_blueprint.route('/show_interactions')
def show_all_interactions():
    # Query the last 100 interactions
    interactions_query = Interaction.query.order_by(Interaction.timestamp.desc()).limit(100).all()

    interactions_data = []
    for interaction in interactions_query:
        # Fetching contact and account details
        contact = Contact.query.get(interaction.contactId)
        account = Account.query.get(interaction.account_id)

        # Structuring data for template
        interaction_data = {
            'timestamp': interaction.timestamp.strftime('%Y-%m-%d %H:%M'),
            'contact_name': contact.Name if contact else "Unknown Contact",
            'account_name': account.Name if account else "Unknown Account",
            'description': interaction.description
        }
        interactions_data.append(interaction_data)

    return render_template('interactions.html', interactions=interactions_data)
