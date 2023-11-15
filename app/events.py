import os
import requests
from datetime import datetime

from flask import Blueprint, redirect, url_for, request, render_template, jsonify
from flask_login import current_user

from app import alerts
from app.forms import EventForm
from app.models import Address, Account, db
from app.models import Event

events_blueprint = Blueprint('events', __name__)

google_maps_api = os.environ.get('GOOGLE_MAPS_API')


@events_blueprint.route('/events_page')
def events_page():
    # Retrieve all events from the database
    # with app.app_context():
    events = Event.query.all()
    # Render the events page and pass the events to the template
    return render_template('events_page.html', events=events)


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


@events_blueprint.route('/add_event', methods=['GET', 'POST'])
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
        # address = Address(
        #     street=street,
        #     city=city,
        #     state=state,
        #     country=country
        # )
        # db.session.add(address)
        # db.session.commit()

        event = Event(
            name=form.name.data,
            description=form.description.data,
            start_time=start_time,
            end_time=end_time,
            audience=form.audience.data,
            event_type=form.event_type.data,

            cost=form.cost.data,
            created_by=current_user.id,
            created_at=datetime.now(),
            sponsor=form.sponsor.data,
            expected_attendees=form.expected_attendees.data,
            actual_attendees=form.actual_attendees.data,
            marketing_channel=form.marketing_channel.data,
            # NEW FORM FIELDS
            registration_link=form.registration_link.data,
            responsibility=form.responsibility.data,
            street_address=parse_location(form.location.data)[0],
            city=parse_location(form.location.data)[1],
            state=parse_location(form.location.data)[2],
            # zip_code=parse_location(form.location.data)[3],
            industry=form.industry.data,
        )

        # Generate an alert
        # generate_event_alert(event)
        # Generate an alert for nearby users
        alerts.generate_event_alert_for_nearby_users(event)

        db.session.add(event)
        db.session.commit()
        return redirect(url_for('events.events_page'))
    return render_template('add_event.html', form=form)


@events_blueprint.route('/event_list/<account_id>/<event_city>')
def event_list(account_id, event_city):
    account = Account.query.get(account_id)
    addresses = Address.query.filter_by(city=event_city).all()
    events = []

    for address in addresses:
        if address.event:
            events.append(address.event)
    return render_template('event_list.html', events=events, account=account)


def get_distance(city1, city2):
    # Define the base URL for the Distance Matrix API
    base_url = "https://maps.googleapis.com/maps/api/distancematrix/json"

    # Define the parameters for the GET request
    params = {
        "origins": city1,
        "destinations": city2,
        "units": "imperial",
        "key": google_maps_api,
    }

    # Send the GET request
    response = requests.get(base_url, params=params)

    # Convert the response to JSON
    data = response.json()

    # Make sure to handle cases where the API returns an error or no routes are found
    if data['status'] == 'OK' and data['rows'][0]['elements'][0]['status'] == 'OK':
        # Extract the distance from the JSON response
        distance = data["rows"][0]["elements"][0]["distance"]["text"]

        # Remove any text from the end of the distance string, remove any commas and convert it to a float
        distance = float(distance.split(" ")[0].replace(",", ""))

        return distance
    else:
        # if this scenario, then return to add event page and flash error message
        return 1000


@events_blueprint.route('/events_in_area', methods=['GET'])
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


@events_blueprint.route('/api/events', methods=['GET'])
def get_events():
    # query all events that are greater than the current time
    events = Event.query.filter(Event.start_time > datetime.now()).all()
    events_list = []
    for event in events:
        events_list.append({
            'name': event.name,
            'description': event.description,
            'start_time': event.start_time,
            'end_time': event.end_time,
            'audience': event.audience,
            'event_type': event.event_type.value,
            'city': event.city,
            'state': event.state,

        })
    events_list.sort(key=lambda x: x['start_time'])
    return jsonify(events_list)
