from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin  # Import UserMixin

db = SQLAlchemy()

class User(db.Model, UserMixin):  # Add UserMixin for Flask-Login compatibility
    __tablename__ = 'users'  # Explicit table name
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    scores = db.relationship('score', back_populates='user')  # Reference to 'score' class

class score(db.Model):  # Using lowercase 'score' as per your database
    __tablename__ = 'quiz_scores'  # Explicit table name for 'score'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    total_questions = db.Column(db.Integer, nullable=False)
    question_type = db.Column(db.String(50), nullable=False)  # e.g., 'mcq', 'fill_in_the_blank', 'both'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', back_populates='scores')  # Reference to 'User' class
