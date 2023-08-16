# Salesforce Integration with Flask

This project demonstrates how to integrate a Flask web application with Salesforce. Users can authenticate via Salesforce and depending on their roles, they can 
access different dashboards. The application retrieves account data from Salesforce using the Salesforce Object Query Language (SOQL).

## Features

- Salesforce OAuth 2.0 authentication
- Role-based access control
- Account data retrieval from Salesforce
- User session management using Flask-Login

## Installation

Before you begin, ensure you have met the following requirements:

- You have a working Python environment (Python 3.6+ is required).
- You have Flask and other dependencies installed. (`flask`, `flask-sqlalchemy`, `flask-login`, `requests`, `dateutil`)

Clone the repository:

```sh
git clone https://github.com/contactatfp/ARRmy---Top-Of-The-Funnel.git


Install the required packages:

sh

pip install -r requirements.txt

Configuration
Update config.json with Salesforce OAuth credentials (Consumer Key, Consumer Secret, and Password).
Set up the environment variables or update app.config for Flask secret key and database configurations.
Usage
Start the Flask development server:

flask run
Open your browser and navigate to http://127.0.0.1:5000.

#Contributing
If you want to contribute to this project, please fork the repository and create a pull request.
