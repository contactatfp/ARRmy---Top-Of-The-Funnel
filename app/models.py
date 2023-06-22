import enum
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

db = SQLAlchemy()


def init_db(app):
    db.init_app(app)
    with app.app_context():
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

    def __repr__(self):
        return f'<Account {self.Name}>'


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
