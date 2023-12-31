import enum
from datetime import datetime
import json
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

db = SQLAlchemy()


def init_db(app):
    db.init_app(app)
    with app.app_context():
        # db.drop_all()
        db.create_all()


class Account(db.Model):
    __tablename__ = 'account'

    Id = db.Column(db.String, primary_key=True)
    IsDeleted = db.Column(db.Boolean)
    MasterRecordId = db.Column(db.String)
    Name = db.Column(db.String)
    Type = db.Column(db.String)
    ParentId = db.Column(db.String)
    BillingStreet = db.Column(db.String)
    BillingCity = db.Column(db.String)
    BillingState = db.Column(db.String)
    BillingPostalCode = db.Column(db.String)
    BillingCountry = db.Column(db.String)
    BillingLatitude = db.Column(db.Float)
    BillingLongitude = db.Column(db.Float)
    BillingGeocodeAccuracy = db.Column(db.String)
    ShippingStreet = db.Column(db.String)
    ShippingCity = db.Column(db.String)
    ShippingState = db.Column(db.String)
    ShippingPostalCode = db.Column(db.String)
    ShippingCountry = db.Column(db.String)
    ShippingLatitude = db.Column(db.Float)
    ShippingLongitude = db.Column(db.Float)
    ShippingGeocodeAccuracy = db.Column(db.String)
    Phone = db.Column(db.String)
    Fax = db.Column(db.String)
    AccountNumber = db.Column(db.String)
    Website = db.Column(db.String)
    PhotoUrl = db.Column(db.String)
    Sic = db.Column(db.String)
    Industry = db.Column(db.String)
    AnnualRevenue = db.Column(db.Float)
    NumberOfEmployees = db.Column(db.Integer)
    Ownership = db.Column(db.String)
    TickerSymbol = db.Column(db.String)
    Description = db.Column(db.String)
    Rating = db.Column(db.String)
    Site = db.Column(db.String)
    OwnerId = db.Column(db.String)
    CreatedDate = db.Column(db.DateTime)
    CreatedById = db.Column(db.String)
    LastModifiedDate = db.Column(db.DateTime)
    LastModifiedById = db.Column(db.String)
    SystemModstamp = db.Column(db.DateTime)
    LastActivityDate = db.Column(db.Date)
    LastViewedDate = db.Column(db.Date)
    LastReferencedDate = db.Column(db.Date)
    Jigsaw = db.Column(db.String)
    JigsawCompanyId = db.Column(db.String)
    CleanStatus = db.Column(db.String)
    AccountSource = db.Column(db.String)
    DunsNumber = db.Column(db.String)
    Tradestyle = db.Column(db.String)
    NaicsCode = db.Column(db.String)
    NaicsDesc = db.Column(db.String)
    YearStarted = db.Column(db.String)
    SicDesc = db.Column(db.String)
    DandbCompanyId = db.Column(db.String)
    OperatingHoursId = db.Column(db.String)
    CustomerPriority__c = db.Column(db.String)
    SLA__c = db.Column(db.String)
    Active__c = db.Column(db.String)
    NumberofLocations__c = db.Column(db.Float)
    UpsellOpportunity__c = db.Column(db.String)
    SLASerialNumber__c = db.Column(db.String)
    SLAExpirationDate__c = db.Column(db.Date)
    Rank = db.Column(db.Integer)
    Notes = db.Column(db.Text)
    Score = db.Column(db.Float)
    Overview = db.Column(db.Text)
    Products = db.Column(db.Text)
    Market = db.Column(db.Text)
    Achievements = db.Column(db.Text)
    IndustryPain = db.Column(db.Text)
    Concerns = db.Column(db.Text)
    OperationalChallenges = db.Column(db.Text)
    LatestNews = db.Column(db.Text)
    RecentEvents = db.Column(db.Text)
    CustomerFeedback = db.Column(db.Text)
    RecentPartnerships = db.Column(db.Text)
    Recommendations = db.Column(db.Text)
    Headcount = db.Column(db.Integer)
    TechColumn = db.Column(db.String)
    IntegrationStatus = db.Column(db.Enum('integration', 'neutral', 'competitor', name='integration_status_enum'))
    SubIndustry = db.Column(db.String)

    def __repr__(self):
        return f'<Account {self.Name}>'


class InvitationStatus(enum.Enum):
    open_invite = "Open Invite"
    attending = "Attending"
    not_attending = "Not Attending"


class Invitation(db.Model):
    __tablename__ = 'invitation'

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'))  # foreign key to Event table
    contact_id = db.Column(db.String, db.ForeignKey('contact.Id'))  # foreign key to Contact table
    account_id = db.Column(db.String, db.ForeignKey('account.Id'))  # foreign key to Account table
    contact_title = db.Column(db.String)  # new column for contact's title
    status = db.Column(db.Enum(InvitationStatus), default=InvitationStatus.open_invite)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    event = db.relationship('Event', backref=db.backref('invitations', lazy=True))
    contact = db.relationship('Contact', backref=db.backref('invitations', lazy=True))
    account = db.relationship('Account', backref=db.backref('invitations', lazy=True))

    def __repr__(self):
        return f'<Invitation {self.id} for Event {self.event_id} to Contact {self.contact_id}>'


class RoleEnum(enum.Enum):
    admin = "admin"
    sales_rep = "sales_rep"
    manager = "manager"
    sdr = "sdr"
    marketing = "marketing"


# User Model
class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.String, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)
    password = db.Column(db.String, nullable=False)
    role = db.Column(db.Enum(RoleEnum), default=RoleEnum.sdr)
    is_active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<User {self.username}>'

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def get_id(self):
        return str(self.id)


class AlertType(enum.Enum):
    manager_comment = "Manager Comment"
    marketing_comment = "Marketing Comment"
    channel_comment = "Channel Comment"
    sdr_comment = "SDR Comment"
    new_event = "New Event"
    account_change = "Account Change"
    in_the_news = "In the News"


class Alert(db.Model):
    __tablename__ = 'alert'

    id = db.Column(db.Integer, primary_key=True)
    alert_type = db.Column(db.Enum(AlertType))
    message = db.Column(db.String)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.String, db.ForeignKey('users.id'))

    user = db.relationship('User', backref=db.backref('alerts', lazy=True))

    def __repr__(self):
        return f'<Alert {self.alert_type}: {self.message}>'


class EventType(enum.Enum):
    company_hosted = "company_hosted"
    third_party = "third_party"


class AttendanceResponsibility(enum.Enum):
    drive_attendance = "Drive Attendance"
    not_responsible = "Not Responsible"


# New Model for Event
class Event(db.Model):
    __tablename__ = 'event'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    description = db.Column(db.String)

    # location = db.relationship('Address', backref='event', uselist=False)
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String, db.ForeignKey('users.id'))
    audience = db.Column(db.Integer)
    event_type = db.Column(db.Enum(EventType))
    responsibility = db.Column(db.Enum(AttendanceResponsibility))
    registration_link = db.Column(db.String)
    street_address = db.Column(db.String)
    city = db.Column(db.String)
    state = db.Column(db.String)

    industry = db.Column(db.String)
    cost = db.Column(db.Float)
    sponsor = db.Column(db.String)
    expected_attendees = db.Column(db.Integer)
    actual_attendees = db.Column(db.Integer)
    marketing_channel = db.Column(db.String)

    created_by_user = db.relationship('User', backref=db.backref('events', lazy=True))

    def __repr__(self):
        return f'<Event {self.name}>'


class Address(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    street = db.Column(db.String(100))
    city = db.Column(db.String(50))
    state = db.Column(db.String(50))
    zip_code = db.Column(db.String(10))
    country = db.Column(db.String(50))
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'))


# New Model for Interaction
class InteractionType(enum.Enum):
    call = "Call"
    email = "Email"
    meeting = "Meeting"

    def to_json(self):
        return self.value


class Interaction(db.Model):
    __tablename__ = 'interaction'

    id = db.Column(db.Integer, primary_key=True)
    interaction_type = db.Column(db.Enum(InteractionType))
    description = db.Column(db.String)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    key_points = db.Column(db.Text)
    sentiment = db.Column(db.Text)
    action_items = db.Column(db.Text)
    account_id = db.Column(db.String, db.ForeignKey('account.Id'))
    user_id = db.Column(db.String, db.ForeignKey('users.id'))
    contactId = db.Column(db.String, db.ForeignKey('contact.Id'))

    account = db.relationship('Account', backref=db.backref('interactions', lazy=True))
    user = db.relationship('User', backref=db.backref('interactions', lazy=True))

    def __repr__(self):
        return f'<Interaction {self.interaction_type} with Account {self.account_id} by User {self.user_id}>'


# New Model for Comment
class Comment(db.Model):
    __tablename__ = 'comment'

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.String, db.ForeignKey('users.id'))

    user = db.relationship('User', backref=db.backref('comments', lazy=True))

    def __repr__(self):
        return f'<Comment by User {self.user_id}: {self.content}>'


class Contact(db.Model):
    __tablename__ = 'contact'

    Id = db.Column(db.String, primary_key=True)
    IsDeleted = db.Column(db.Boolean)
    MasterRecordId = db.Column(db.String)
    AccountId = db.Column(db.String, db.ForeignKey('account.Id'))
    LastName = db.Column(db.String)
    FirstName = db.Column(db.String)
    Salutation = db.Column(db.String)
    Name = db.Column(db.String)
    MailingStreet = db.Column(db.String)
    MailingCity = db.Column(db.String)
    MailingState = db.Column(db.String)
    MailingPostalCode = db.Column(db.String)
    MailingCountry = db.Column(db.String)
    MailingLatitude = db.Column(db.Float)
    MailingLongitude = db.Column(db.Float)
    MailingGeocodeAccuracy = db.Column(db.String)
    Phone = db.Column(db.String)
    Fax = db.Column(db.String)
    MobilePhone = db.Column(db.String)
    HomePhone = db.Column(db.String)
    OtherPhone = db.Column(db.String)
    AssistantPhone = db.Column(db.String)
    ReportsToId = db.Column(db.String)
    Email = db.Column(db.String)
    Title = db.Column(db.String)
    Department = db.Column(db.String)
    AssistantName = db.Column(db.String)
    LeadSource = db.Column(db.String)
    Birthdate = db.Column(db.Date)
    Description = db.Column(db.String)
    OwnerId = db.Column(db.String)
    CreatedDate = db.Column(db.DateTime)
    CreatedById = db.Column(db.String)
    LastModifiedDate = db.Column(db.DateTime)
    LastModifiedById = db.Column(db.String)
    SystemModstamp = db.Column(db.DateTime)
    LastActivityDate = db.Column(db.Date)
    LastCURequestDate = db.Column(db.Date)
    LastCUUpdateDate = db.Column(db.Date)
    LastViewedDate = db.Column(db.Date)
    LastReferencedDate = db.Column(db.Date)
    EmailBouncedReason = db.Column(db.String)
    EmailBouncedDate = db.Column(db.Date)
    IsEmailBounced = db.Column(db.Boolean)
    PhotoUrl = db.Column(db.String)
    Jigsaw = db.Column(db.String)
    JigsawContactId = db.Column(db.String)
    CleanStatus = db.Column(db.String)
    IndividualId = db.Column(db.String)
    Level__c = db.Column(db.String)
    Languages__c = db.Column(db.String)
    JobRank = db.Column(db.Integer)
    Recommendation = db.Column(db.Text)

    IsPartnerRep = db.Column(db.Boolean, default=False)
    LinkedInUrl = db.Column(db.String)

    def __repr__(self):
        return f'<Contact {self.Name}>'


class AccountActivity(db.Model):
    __tablename__ = 'account_activity'
    Id = db.Column(db.Integer, primary_key=True)
    AccountId = db.Column(db.String, db.ForeignKey('account.Id'))
    ActivityType = db.Column(db.Enum('meeting', 'call', 'email', name='activity_type_enum'))
    Date = db.Column(db.DateTime, default=datetime.utcnow)
    Details = db.Column(db.Text)


# Association table for many-to-many relationship between CustomerStory and Account
story_account_association = db.Table('story_account_association',
                                     db.Column('story_id', db.Integer, db.ForeignKey('customer_story.id')),
                                     db.Column('account_id', db.String, db.ForeignKey('account.Id')),
                                     db.Column('icp_score', db.Integer)  # ICP score ranging from 0-5
                                     )


class CustomerStory(db.Model):
    __tablename__ = 'customer_story'

    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String)
    champion_title = db.Column(db.String)
    location = db.Column(db.String)
    industry = db.Column(db.String)
    company_size = db.Column(db.Integer)
    technologies = db.Column(db.String)  # Assuming a comma-separated list of known technologies
    products_purchased = db.Column(db.String)  # Assuming a comma-separated list of products/use cases

    # Defining many-to-many relationship with Account
    accounts = db.relationship('Account', secondary=story_account_association, backref='customer_stories')

    def __repr__(self):
        return f'<CustomerStory {self.customer_name}>'


# New Model for FeedItem
class FeedItemType(enum.Enum):
    interaction_summary = "Interaction Summary"
    alert = "Alert"
    focus = "Focus"
    # add other types of feed items as needed


class FeedItem(db.Model):
    __tablename__ = 'feed_item'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'))  # foreign key to User table
    feed_item_type = db.Column(db.Enum(FeedItemType))
    content = db.Column(db.String)  # Content of the feed item
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('feed_items', lazy=True))
    alert_contacts = db.Column(db.Text)  # New field to store contact IDs

    def set_alert_contacts(self, contacts):
        self.alert_contacts = json.dumps([contact.Id for contact in contacts])

    def get_alert_contacts(self):
        return json.loads(self.alert_contacts) if self.alert_contacts else []

    def __repr__(self):
        return f'<FeedItem {self.id} for User {self.user_id}>'
