import os

from celery import Celery

from dotenv import load_dotenv
from flask import Flask
from flask_apscheduler import APScheduler
from flask_migrate import Migrate
from flask_socketio import SocketIO
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*")

from app.accounts import accounts_blueprint
from app.authentication import auth_blueprint
from app.authentication import init_login_manager
from app.contacts import contacts_blueprint
from app.events import events_blueprint
from app.feed import feed_blueprint
from app.interactions import interactions_blueprint
from app.invitations import invitations_blueprint
from app.models import db, init_db
from app.prospecting import bio_blueprint
from app.utils import cache, util_blueprint
from app.views import views_blueprint
# from app.voice_assist import voice_blueprint
from app.alerts import alerts_blueprint
from app.twilio_api import twilio_blueprint

app.register_blueprint(bio_blueprint)
# app.register_blueprint(voice_blueprint)
app.register_blueprint(feed_blueprint)
app.register_blueprint(auth_blueprint)
app.register_blueprint(events_blueprint)
app.register_blueprint(accounts_blueprint)
app.register_blueprint(contacts_blueprint)
app.register_blueprint(invitations_blueprint)
app.register_blueprint(views_blueprint)
app.register_blueprint(interactions_blueprint)
app.register_blueprint(util_blueprint)
app.register_blueprint(alerts_blueprint)
app.register_blueprint(twilio_blueprint)

init_login_manager(app)
# socketio.init_app(app)


# cache = Cache(config={'CACHE_TYPE': 'simple'})
cache.init_app(app)
load_dotenv()

scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

openai_api_key = os.getenv("OPENAI_API_KEY")
consumer_key = os.getenv("CONSUMER_KEY")
consumer_secret = os.getenv("CONSUMER_SECRET")
google_maps_api = os.getenv("GOOGLE_MAPS_API")
google_api_key = os.getenv("GOOGLE_API_KEY")
google_cse_id = os.getenv("GOOGLE_CSE_ID")
serper_api_key = os.getenv("SERPER_API_KEY")
username = os.getenv("USERNAME")
password = os.getenv("PASSWORD")


class Config:
    SCHEDULER_API_ENABLED = True


app.config.from_object(Config)

scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

migrate = Migrate(app, db)

# Configure your app
app.config.from_object('app.config')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.getenv("SECRET_KEY")

# Initialize the database
init_db(app)


# login_manager = LoginManager()
# login_manager.init_app(app)
# login_manager.login_view = 'login'


def make_celery(app):
    celery = Celery(
        app.import_name,
        backend=app.config['CELERY_RESULT_BACKEND'],
        broker=app.config['BROKER_URL']
    )
    celery.conf.update(app.config)
    return celery


app.config.from_object('app.celery_config')
celery = make_celery(app)

DOMAIN = "https://fakepicasso-dev-ed.develop.my.salesforce.com"
SALESFORCE_API_ENDPOINT = "/services/data/v58.0/sobjects/"
SALESFORCE_API_OPPS = "/services/data/v58.0/graphql"

if __name__ == '__main__':
    app.run()
