from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user
import json
from datetime import datetime, timedelta


feed_blueprint = Blueprint('feed', __name__, template_folder='templates')

with open('config.json') as f:
    config = json.load(f)


# Mock functions to fetch data. You can replace them with real database calls.
def fetch_recommendations(limit=10, offset=0):
    # Replace with your actual database calls
    return [{'text': 'Sample Recommendation', 'account': 'Sample Account', 'score': 5}] * limit


def fetch_events(limit=10, offset=0):
    # Replace with your actual database calls
    return [{'text': 'Sample Event'}] * limit


def fetch_alerts(limit=10, offset=0):
    from app.models import FeedItem, FeedItemType, db
    alerts = db.session.query(FeedItem).filter(
        FeedItem.feed_item_type == FeedItemType.alert,
        FeedItem.user_id == current_user.id
    ).limit(limit).offset(offset).all()

    beautified_alerts = []
    for alert in alerts:
        # Your logic to beautify the text, for example:
        beautified_text = alert.content.replace('<Contact ', '').replace('>', '')

        # Include alert_contacts in the output
        alert_contacts = alert.get_alert_contacts()  # Assuming you have a method that can fetch and deserialize the alert_contacts

        beautified_alerts.append({
            'text': beautified_text,
            'alert_contacts': alert_contacts
        })

    return beautified_alerts




def fetch_meetings(limit=10, offset=0):
    # Replace with your actual database calls
    return [{'text': 'Sample Meeting'}] * limit


def interaction_previous_week(limit=10, offset=0):
    from app.models import FeedItem, FeedItemType, db  # Make sure to import the necessary models
    user_id = current_user.id

    # Check if a summary exists in the last 24 hours
    last_24_hours = datetime.utcnow() - timedelta(hours=24)
    existing_summary = FeedItem.query.filter(
        FeedItem.user_id == user_id,
        FeedItem.feed_item_type == FeedItemType.interaction_summary,
        FeedItem.created_at >= last_24_hours
    ).first()

    if existing_summary:
        return [{'text': existing_summary.content}] * 1
    from langchain.chat_models import ChatOpenAI
    from langchain.utilities import SQLDatabase
    from langchain_experimental.sql import SQLDatabaseChain
    db2 = SQLDatabase.from_uri("sqlite:///instance/sfdc.db")
    llm = ChatOpenAI(temperature=0, model="gpt-3.5-turbo-16k", verbose=True, openai_api_key=config['openai_api-key'])
    db_chain = SQLDatabaseChain.from_llm(llm, db2, verbose=True)

    summary = db_chain.run(f'''
    How many interactions were timestamped within the last week? The format should be as follows:
    
    Week of <date> to <date>
    Calls: <number of calls>
    Emails: <number of emails>
    Meetings: <number of meetings>
    
    Action Items: <summary of any action items from the interactions>
    
    If there are not any Interactions for the week then return "No Interactions Last Week"
    ''')

    # Create new FeedItem object
    new_feed_item = FeedItem()
    new_feed_item.user_id = user_id
    new_feed_item.feed_item_type = FeedItemType.interaction_summary
    new_feed_item.content = summary

    # Add new FeedItem to session and commit
    db.session.add(new_feed_item)
    db.session.commit()

    return [{'text': summary}] * 1


@feed_blueprint.route('/feed', methods=['GET'])
def feed():
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Number of items per page

    # Now fetch data based on the page number
    recommendations = fetch_recommendations(limit=per_page, offset=(page - 1) * per_page)
    events = fetch_events(limit=per_page, offset=(page - 1) * per_page)
    alerts = fetch_alerts(limit=per_page, offset=(page - 1) * per_page)
    # meetings = fetch_meetings(limit=per_page, offset=(page - 1) * per_page)
    meetings = interaction_previous_week(limit=per_page, offset=(page - 1) * per_page)

    # Return data as JSON
    return jsonify({
        # 'recommendations': recommendations,
        # 'events': events,
        # 'alerts': [alert.content for alert in alerts],
        'alerts': alerts,
        # 'meetings': meetings,
        'meetings': meetings
    })
