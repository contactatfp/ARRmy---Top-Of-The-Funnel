from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user
from dotenv import load_dotenv
import os

from datetime import datetime, timedelta
from flask import Markup

feed_blueprint = Blueprint('feed', __name__, template_folder='templates')

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")


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
        FeedItem.feed_item_type.in_([FeedItemType.alert, FeedItemType.focus]),
        FeedItem.user_id == current_user.id
    ).limit(limit).offset(offset).all()

    beautified_alerts = []
    for alert in alerts:
        # Your logic to beautify the text, for example:
        beautified_text = alert.content.replace('<Contact ', '').replace('>', '')
        title = alert.feed_item_type.value
        date = alert.created_at.strftime('%b %d, %Y')

        # Include alert_contacts in the output
        alert_contacts = alert.get_alert_contacts()

        beautified_alerts.append({
            'text': beautified_text,
            'alert_contacts': alert_contacts,
            'title': title,
            'date': date
        })

    return beautified_alerts


def fetch_meetings(limit=10, offset=0):
    # Replace with your actual database calls
    return [{'text': 'Sample Meeting'}] * limit


import json  # Add this import at the top of your file if it's not already there


def interaction_previous_week(limit=10, offset=0):
    from app.models import FeedItem, FeedItemType, db
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
    summary, contacts = reg_sql()

    # Create new FeedItem object
    new_feed_item = FeedItem()
    new_feed_item.user_id = user_id
    new_feed_item.feed_item_type = FeedItemType.interaction_summary
    new_feed_item.content = summary
    new_feed_item.alert_contacts = json.dumps(contacts)  # Serialize the list to JSON

    # Add new FeedItem to session and commit
    db.session.add(new_feed_item)
    db.session.commit()

    return [{'text': summary}] * 1


def reg_sql():
    from app.models import db
    from sqlalchemy import text

    sql_query = text('''
    SELECT 
        "interaction_type", 
        COUNT("interaction_type") as "Count", 
        GROUP_CONCAT("description", '; ') as "ActionItems",
        GROUP_CONCAT("contactId", ', ') as "ContactIds" 
    FROM 
        interaction 
    WHERE 
        "timestamp" BETWEEN datetime('now', '-7 days') AND datetime('now') 
    GROUP BY 
        "interaction_type"
    '''.strip())

    # Get a connection and execute the query
    connection = db.engine.connect()
    result = connection.execute(sql_query)
    connection.close()

    # Convert the result into a list of dictionaries for easier manipulation
    keys = result.keys()
    summaries = [dict(zip(keys, row)) for row in result]
    action_items_list = []
    contactIdsList = []

    num_calls = 0
    num_emails = 0
    num_meetings = 0

    # Loop through each summary to populate the counts and action items
    for summary in summaries:
        if summary['interaction_type'] == 'call':
            num_calls = summary['Count']
            action_items_list.append(f"<li>From Calls: {summary['ActionItems']}</li>")
        elif summary['interaction_type'] == 'email':
            num_emails = summary['Count']
            action_items_list.append(f"<li>From Emails: {summary['ActionItems']}</li>")
        elif summary['interaction_type'] == 'meeting':
            num_meetings = summary['Count']
            action_items_list.append(f"<li>From Meetings: {summary['ActionItems']}</li>")
        contactIdsList.extend(summary['ContactIds'].split(', '))

    # Get the date range for the last week
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)

    # Format the date range and action items
    date_range = f"Week of {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
    formatted_action_items = "".join(action_items_list)
    weekly_summary = 'Weekly Summary'
    # Create the final formatted summary in HTML
    formatted_summary = Markup(f"""
    <div class='card-header'>
        <span class='date'>{date_range}</span>
        <span class='card-status-summary'>{weekly_summary}</span>
    </div>
    <div class='card-body'>
        <p>Calls: {num_calls}</p>
        <p>Emails: {num_emails}</p>
        <p>Meetings: {num_meetings}</p>
        <span class='date'>Action Items:</span>
        <ul>{formatted_action_items}</ul>
    </div>
    """)

    return formatted_summary, contactIdsList


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
