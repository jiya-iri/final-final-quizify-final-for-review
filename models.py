from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(db.Model, UserMixin):  # Add UserMixin for Flask-Login compatibility
    __tablename__ = 'users'  # Explicit table name

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    # Relationship to quiz scores
    scores = db.relationship('score', back_populates='user')  # Corrected class name to 'Score'

class score(db.Model):  # Use PascalCase for the class name (Score)
    __tablename__ = 'quiz_scores'  # Explicit table name for 'quiz_scores'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Foreign key referencing 'users'
    score = db.Column(db.Integer, nullable=False)  # The score for the quiz
    total_questions = db.Column(db.Integer, nullable=False)  # Total questions in the quiz
    question_type = db.Column(db.String(50), nullable=False)  # e.g., 'mcq', 'fill_in_the_blank', 'both'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)  # Timestamp of when the score was recorded

    user = db.relationship('User', back_populates='scores')  # Reference to 'User' class
