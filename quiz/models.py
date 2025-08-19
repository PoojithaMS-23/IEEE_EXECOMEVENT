from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'user'  # safe with Supabase if you already created it like this

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    team_number = db.Column(db.Integer, nullable=False)
    current_round = db.Column(db.Integer, default=1)
    total_score = db.Column(db.Integer, default=0)
    last_question_time = db.Column(db.Float)

    answers = db.relationship('Answer', backref='user', lazy=True)

class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    round_number = db.Column(db.Integer)  # Question number (1 to 6)
    answer = db.Column(db.String)
    correct = db.Column(db.Boolean)
    submission_time = db.Column(db.Float)
    points = db.Column(db.Integer)  # 5 or 10 depending on the question
