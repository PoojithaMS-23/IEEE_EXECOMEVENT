from flask import Flask, render_template, request, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
import time
import json
import os
from dotenv import load_dotenv
import random

def get_user_questions(team_number, username):
    questions_copy = QUESTIONS.copy()
    seed_value = f"{team_number}-{username}"
    random.seed(seed_value)
    random.shuffle(questions_copy)
    return questions_copy

    
    # Append the fixed question at the end
    questions_copy.append(fixed_question)
    
    return questions_copy



load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", "sqlite:///quiz.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
print("Using secret key:", app.config['SECRET_KEY'])

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)

# MODELS

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    team_number = db.Column(db.Integer, nullable=False)
    current_round = db.Column(db.Integer, default=0)
    total_score = db.Column(db.Integer, default=0)
    last_question_time = db.Column(db.Float)

class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    round_number = db.Column(db.Integer)
    answer = db.Column(db.String)
    correct = db.Column(db.Boolean)
    submission_time = db.Column(db.Float)
    points = db.Column(db.Integer)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Load questions
with open("questions.json") as f:
    QUESTIONS = json.load(f)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        team_number = request.form['team_number']
        
        # Validate team number
        try:
            team_number = int(team_number)
            if team_number <= 0:
                return "Team number must be a positive integer"
        except ValueError:
            return "Team number must be a valid integer"
        
        user = User.query.filter_by(username=username).first()

        if user:
            # User exists, just log them in
            login_user(user)
            return redirect(url_for('question'))
        else:
            # Register new user
            user = User(username=username, team_number=team_number, last_question_time=time.time())
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for('question'))
    
    return render_template('login.html')

@app.route('/question', methods=['GET', 'POST'])
@login_required
def question():
    # Get shuffled questions unique per user in the team
    user_questions = get_user_questions(current_user.team_number, current_user.username)

    if current_user.current_round >= len(user_questions):
        return redirect(url_for('scoreboard'))

    question = user_questions[current_user.current_round]

    # Set timer: 10 minutes if question id == 5 else 5 minutes
    if question.get('id') == 5:
        allowed_time = 10 * 60
    else:
        allowed_time = 5 * 60

    if request.method == 'POST':
        submitted_answer = request.form['answer'].strip().lower()
        correct_answer = question['answer'].strip().lower()

        now = time.time()
        time_taken = now - current_user.last_question_time

        if time_taken <= allowed_time and submitted_answer == correct_answer:
            points = 5  # or your existing logic here
            is_correct = True
        else:
            points = 0
            is_correct = False

        new_answer = Answer(
            user_id=current_user.id,
            round_number=current_user.current_round + 1,
            answer=submitted_answer,
            correct=is_correct,
            submission_time=now,
            points=points
        )
        db.session.add(new_answer)

        current_user.total_score += points
        current_user.current_round += 1
        current_user.last_question_time = now
        db.session.commit()

        return redirect(url_for('question'))

    return render_template(
        'question.html',
        question=question,
        round_num=current_user.current_round + 1,
        allowed_time=allowed_time
    )

@app.route('/scoreboard')
def scoreboard():
    users = User.query.order_by(User.total_score.desc()).all()
    return render_template('scoreboard.html', users=users)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/toppers')
def toppers():
    # Subquery: max score per team
    subquery = db.session.query(
        User.team_number,
        db.func.max(User.total_score).label('top_score')
    ).group_by(User.team_number).subquery()

    # Join subquery to find users with that top score in each team
    toppers = db.session.query(User).join(
        subquery,
        (User.team_number == subquery.c.team_number) &
        (User.total_score == subquery.c.top_score)
    ).order_by(User.team_number).all()

    return render_template('toppers.html', toppers=toppers)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
