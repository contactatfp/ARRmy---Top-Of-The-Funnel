from datetime import datetime
from operator import and_

from flask_login import current_user
from app import events
from app.models import Alert, AlertType, Account, Contact, FeedItem, FeedItemType, db
from flask import Blueprint, jsonify, render_template, request

alerts_blueprint = Blueprint('alerts', __name__, template_folder='templates')


def generate_event_alert_for_nearby_users(event):
    miles_from_event = 50  # Distance in miles
    alert_contacts = []
    user_id = current_user.id  # Assuming this is the same for all accounts
    alert_message = f"The {event.name} event is now open for registration. It will be held in {event.city}, {event.state} on {event.start_time}."

    accounts = Account.query.all()

    for account in accounts:
        if not (account.BillingCity and event.city):
            continue

        distance = events.get_distance(account.BillingCity, event.city)

        if distance > miles_from_event:
            continue

        if event.event_type == "company_hosted":
            contacts = Contact.query.filter(
                Contact.AccountId == account.Id,
                Contact.JobRank >= event.audience
            ).all()
            alert_contacts += contacts

    if event.event_type == "company_hosted" and alert_contacts:
        alert_message += f"<br> Signup here: <a href='{event.registration_link}'>{event.registration_link}</a>."
        alert_message += f"<br> Here is a list of contacts that are suitable for the event: {alert_contacts}"

    feed_item = FeedItem(user_id=user_id, feed_item_type=FeedItemType.alert, content=alert_message)
    feed_item.set_alert_contacts(alert_contacts)
    db.session.add(feed_item)
    db.session.commit()


@alerts_blueprint.route('/account_focus', methods=['POST'])
def account_focus():
    data = request.get_json()
    account_id = data.get('accountId')
    account = Account.query.get(account_id)

    # Check if a FeedItem already exists for this account
    existing_item = FeedItem.query.filter(
        and_(
            FeedItem.feed_item_type == FeedItemType.focus,
            FeedItem.content.like(f'%{account.Name}%')
        )
    ).first()

    if existing_item:
        # Delete the FeedItem if it exists
        db.session.delete(existing_item)
        db.session.commit()
        return jsonify({'message': 'FeedItem deleted'}), 200
    else:
        contact_ids = []
        contacts = Contact.query.filter_by(AccountId=account_id).all()

        for contact in contacts:
            contact_ids.append(contact.Id)

        alert = FeedItem(
            user_id=current_user.id,
            feed_item_type=FeedItemType.focus,
            content=f'Focus on {account.Name} ',
            created_at=datetime.now(),
        )
        alert.set_alert_contacts(contacts)  # Use the set_alert_contacts method here

        db.session.add(alert)
        db.session.commit()

    return jsonify(
        {'contact_ids': contact_ids, 'account_id': account_id, 'alert_type': 'focus', 'content': f'Focus on {account.Name} ',
         'date': datetime.now()})

