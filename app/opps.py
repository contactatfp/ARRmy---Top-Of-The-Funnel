from flask import Flask, request, jsonify, Blueprint
import requests
from datetime import datetime, timedelta
from app.tokens import tokens

opps_blueprint = Blueprint('opps', __name__)


@opps_blueprint.route('/won', methods=['GET', 'POST'])
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


@opps_blueprint.route('/open', methods=['GET', 'POST'])
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


@opps_blueprint.route('/open_with_amount', methods=['GET', 'POST'])
def get_open_opps_with_amount(days_ago=365):
    url = "https://fakepicasso-dev-ed.develop.my.salesforce.com/services/data/v58.0/graphql"
    payload = "{\"query\":\"query opportunitiesNotClosed {\\n  uiapi {\\n    query {\\n      Opportunity(\\n        where: {\\n          not: {\\n            or: [\\n              { StageName: { eq: \\\"Closed Won\\\" } }\\n              { StageName: { eq: \\\"Closed Lost\\\" } }\\n            ]\\n          }\\n        }\\n      ) {\\n        edges {\\n          node {\\n            Id\\n            Account {  # Add this line\\n              Name {  # And this line\\n                value\\n              }\\n              Id\\n            }\\n            # NextStep {\\n            #   value\\n            # }\\n            CloseDate {\\n              value\\n            #   displayValue\\n            }\\n            # Description {\\n            #   value\\n            # }\\n            Amount{\\n                value\\n            }\\n            StageName {\\n              value\\n            }\\n          }\\n        }\\n      }\\n    }\\n  }\\n}\\n\",\"variables\":{}}"
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

    # Define the end date as today + days_ago
    end_date = datetime.today().date() + timedelta(days=days_ago)

    # Filter opportunities based on CloseDate
    filtered_opportunities = []
    for opportunity in opportunities:
        close_date_str = opportunity["node"]["CloseDate"]["value"]
        close_date = datetime.strptime(close_date_str, "%Y-%m-%d").date()
        if end_date >= close_date >= datetime.today().date():
            filtered_opportunities.append(opportunity)

    return filtered_opportunities


@opps_blueprint.route('/closed_value', methods=['GET', 'POST'])
def get_closed_won_opps_value(days_ago=365):
    url = "https://fakepicasso-dev-ed.develop.my.salesforce.com/services/data/v58.0/graphql"

    token = tokens()
    if not token:
        return {"error": "Failed to get Salesforce token"}
    else:
        token = token['access_token']
    payload = "{\"query\":\"query opportunitiesClosedWon {\\n  uiapi {\\n    query {\\n      Opportunity(\\n        where: {\\n          StageName: { eq: \\\"Closed Won\\\" }\\n        }\\n      ) {\\n        edges {\\n          node {\\n            Id\\n            Account {\\n              Name {\\n                value\\n              }\\n              Id \\n            }\\n            CloseDate {\\n              value\\n            }\\n            StageName {\\n              value\\n            }\\n            Amount {\\n              value\\n            }\\n          }\\n        }\\n      }\\n    }\\n  }\\n}\\n\",\"variables\":{}}"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}',
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    response_json = response.json()
    opportunities = response_json["data"]["uiapi"]["query"]["Opportunity"]["edges"]

    # The filtering logic for the opportunities based on CloseDate can be added here as needed

    return opportunities


@opps_blueprint.route('/closed_total', methods=['GET', 'POST'])
def get_closed_won_opps_total(days_ago):
    opps = get_closed_won_opps_value(days_ago)
    total = 0
    for opp in opps:
        opp["node"]["Amount"]["value"] = float(opp["node"]["Amount"]["value"])
        #         total of all closed opps looping through the list
        total += opp["node"]["Amount"]["value"]

    return total


@opps_blueprint.route('/open_value', methods=['GET', 'POST'])
def get_open_opps_value(days_ago=365):
    opportunities = get_open_opps_with_amount(days_ago)

    total = 0
    for opportunity in opportunities:
        # Check if "Amount" key exists before processing
        if "Amount" in opportunity["node"] and "value" in opportunity["node"]["Amount"]:
            opportunity["node"]["Amount"]["value"] = float(opportunity["node"]["Amount"]["value"])
            total += opportunity["node"]["Amount"]["value"]

    return total


@opps_blueprint.route('/create_opp', methods=['GET', 'POST'])
def create_opportunity():
    # Define the endpoint URL for creating a new Opportunity
    url = "https://fakepicasso-dev-ed.develop.my.salesforce.com/services/data/v58.0/sobjects/Opportunity"

    # Define the Opportunity data
    data = {
        "Name": "Test Opportunity",
        "CloseDate": "2023-10-10",
        "StageName": "Prospecting",
        "Amount": 10000
    }
    token = tokens()
    token = token['access_token']
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 201:
        return response.json()  # Returns the ID of the newly created Opportunity
    else:
        return response.text  # Returns the error message