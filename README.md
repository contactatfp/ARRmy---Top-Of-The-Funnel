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
git clone <REPO_LINK>
cd <REPO_DIRECTORY>

