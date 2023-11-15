import os
import requests

consumer_key = os.getenv("CONSUMER_KEY")
consumer_secret = os.getenv("CONSUMER_SECRET")
username = os.getenv("USERNAME")
password = os.getenv("PASSWORD")

DOMAIN = "https://fakepicasso-dev-ed.develop.my.salesforce.com"
# DOMAIN = "https://test.salesforce.com"

def get_user_token(username, pw):
    try:
        payload = {
            'grant_type': 'password',
            'client_id': consumer_key,
            'client_secret': consumer_secret,
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


def tokens():
    try:
        payload = {
            'grant_type': 'password',
            'client_id': consumer_key,
            'client_secret': consumer_secret,
            'username': username,
            'password': password
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

# @app.route('/get_data', methods=['GET'])
# @login_required
# def get_data():
#
#     token = tokens()
#     if not token:
#         return {"error": "Failed to get Salesforce token"}
#
#     for model, api_endpoint in [(Account, "account"), (Contact, "contact"), (Interaction, "interaction"),
#                                 (Event, "event"), (Address, "address")]:
#         url = f"{DOMAIN}/services/data/v58.0/queryAll/?q=SELECT+name,id+from+{api_endpoint}"
#         response = create_api_request("GET", url, token['access_token'])
#         process_response(response, model)
#
#     return jsonify({"success": True})