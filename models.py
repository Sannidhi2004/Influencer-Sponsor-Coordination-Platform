from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime


app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///your_database.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

db = SQLAlchemy(app)

influencer_campaign_association = db.Table('influencer_campaign_association',
    db.Column('influencer_id', db.Integer, db.ForeignKey('influencer.id')),
    db.Column('campaign_id', db.Integer, db.ForeignKey('campaign.id'))
)


class User(UserMixin, db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    username = db.Column(db.String(150), nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    
    influencers = db.relationship('Influencer', back_populates='user', viewonly=True)

    def get_id(self):
        return str(self.id)

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def __repr__(self):
        return f"<User {self.username}>"

class Influencer(db.Model):
    __tablename__ = "influencer"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(64), nullable=False)
    platform = db.Column(db.String(64), nullable=False)
    niche = db.Column(db.String(64), nullable=False)
    reach = db.Column(db.Integer, nullable=False)
    profile_picture = db.Column(db.String(128))
    
    campaigns = db.relationship('Campaign', secondary=influencer_campaign_association,
                                back_populates='associated_influencers')   
    user = db.relationship('User', back_populates='influencers')
    ads = db.relationship('Ad', backref='influencer', lazy=True)

    def __repr__(self):
        return f"Influencer('{self.name}', '{self.platform}', '{self.niche}', '{self.reach}')"

class Section(db.Model):
    __tablename__ = "section"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class Campaign(db.Model):
    __tablename__ = "campaign"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    description = db.Column(db.String(84), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    budget = db.Column(db.Integer, nullable=False)
    visibility = db.Column(db.String(84), nullable=False)
    goals = db.Column(db.String(84), nullable=False)
    niche = db.Column(db.String(64), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    associated_influencers = db.relationship('Influencer', secondary=influencer_campaign_association,
                                             back_populates='campaigns')
    
    ads = db.relationship('Ad', backref='campaign', lazy=True)
    
    user = db.relationship('User', backref='campaigns')

    def __repr__(self):
        return f"Campaign('{self.name}', '{self.start_date}', '{self.end_date}', '{self.budget}', '{self.visibility}', '{self.niche}')"

class Ad(db.Model):
    __tablename__ = 'ad'
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'), nullable=False)
    influencer_id = db.Column(db.Integer, db.ForeignKey('influencer.id'), nullable=False)
    messages = db.Column(db.Text, nullable=False)
    requirements = db.Column(db.Text)
    payment_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Pending')  # Pending, Accepted, Rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"Ad('{self.messages}', '{self.requirements}', '{self.payment_amount}', '{self.status}')"
    
class Transaction(db.Model):
    __tablename__ = 'transaction'
    id = db.Column(db.Integer, primary_key=True)
    influencer_id = db.Column(db.Integer, db.ForeignKey('influencer.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), nullable=False)
    ad_request_id = db.Column(db.Integer, db.ForeignKey('ad.id'), nullable=True)
    request_type = db.Column(db.String(50), nullable=False)
    
    influencer = db.relationship('Influencer', backref='transactions')
    user = db.relationship('User', backref='transactions')
    ad_request = db.relationship('Ad', backref='transactions', uselist=False)
    
    def __repr__(self):
        return f"Transaction('{self.influencer_id}', '{self.user_id}', '{self.amount}', '{self.date}', '{self.status}', '{self.ad_request_id}', '{self.request_type}')"

class Bookmark(db.Model):
    __tablename__ = 'bookmark'
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    campaign = db.relationship('Campaign', backref='bookmarks')
    user = db.relationship('User', backref='bookmarks')
    
    def __repr__(self):
        return f"Bookmark('{self.campaign_id}', '{self.user_id}')"

class Rating(db.Model):
    __tablename__ = 'rating'
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transaction.id'), nullable=False)
    rater_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    ratee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    review = db.Column(db.Text)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    
    transaction = db.relationship('Transaction', backref='ratings')
    rater = db.relationship('User', foreign_keys=[rater_id], backref='given_ratings')
    ratee = db.relationship('User', foreign_keys=[ratee_id], backref='received_ratings')
    
class Flag(db.Model):
    __tablename__ = 'flag'
    id = db.Column(db.Integer, primary_key=True)
    item_type = db.Column(db.String(50), nullable=False)  # e.g., 'Influencer', 'Sponsor', 'Campaign'
    item_id = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Flag {self.item_type} ID {self.item_id}>"
    
 
    def __repr__(self):
        return f"Rating('{self.transaction_id}', '{self.rater_id}', '{self.ratee_id}', '{self.rating}', '{self.review}', '{self.date}')"

