from flask import Flask, request, jsonify, session, send_from_directory, redirect, url_for
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import yt_dlp
import whisper
from transformers import pipeline
import os
import nltk
from text_to_quiz import generate_quiz
from models import User, score, db  # Ensure models are correctly imported
from datetime import timedelta

# Setup
nltk.download('punkt')

# App setup
app = Flask(__name__, static_folder='fe')
CORS(app, supports_credentials=True)

# Configurations
app.secret_key = "your_secret_key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)  # Session timeout setting

# Initialize extensions
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)

# Initialize database
db.init_app(app)

# Set the login view for Flask-Login
login_manager.login_view = 'auth_form'

# -------------------------------
# User loader for Flask-Login
# -------------------------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# -------------------------------
# Auth Routes
# -------------------------------

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "User already exists"}), 409

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    new_user = User(email=email, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": "User registered successfully"}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    user = User.query.filter_by(email=email).first()
    if user and bcrypt.check_password_hash(user.password, password):
        login_user(user, remember=True)  # Keep user logged in across sessions
        return jsonify({"message": "Login successful"}), 200
    return jsonify({"error": "Invalid email or password"}), 401

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logout successful"}), 200

# -------------------------------
# YouTube Summarizer Logic
# -------------------------------

def download_audio(youtube_url, output_path="audio.mp3"):
    ydl_opts = {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'outtmpl': output_path,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])
        print(f"✅ Audio downloaded successfully to {output_path}")
    except Exception as e:
        print(f"❌ Failed to download audio: {e}")
        raise e

def transcribe_audio(audio_path):
    print("⏳ Loading Whisper model...")
    model = whisper.load_model("base")
    print("🔍 Transcribing audio...")
    result = model.transcribe(audio_path)
    transcription = result["text"]
    print("✅ Transcription completed!")

    output_file = "transcription.txt"
    with open(output_file, "w", encoding="utf-8") as file:
        file.write(transcription)
        print(f"📝 Transcription saved to {output_file}")
    return transcription

def summarize_text(text, max_chunk_length=1000):
    summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

    from nltk import sent_tokenize
    sentences = sent_tokenize(text)
    chunks = []
    current_chunk = ""

    for sentence in sentences:
        if len(current_chunk) + len(sentence) <= max_chunk_length:
            current_chunk += " " + sentence
        else:
            chunks.append(current_chunk.strip())
            current_chunk = sentence

    if current_chunk:
        chunks.append(current_chunk.strip())

    print(f"📝 Text split into {len(chunks)} chunks for summarization.")
    summaries = []
    for i, chunk in enumerate(chunks):
        print(f"🔍 Summarizing chunk {i + 1}/{len(chunks)}...")
        summary = summarizer(chunk, max_length=200, min_length=50, do_sample=False)[0]['summary_text']
        summaries.append(summary)

    final_summary = " ".join(summaries)
    return final_summary

def summarize_youtube_video(youtube_url):
    try:
        audio_path = "audio.mp3"
        download_audio(youtube_url, audio_path)

        transcription = transcribe_audio(audio_path)
        print(f"📖 Transcription Length: {len(transcription.split())} words")

        summary = summarize_text(transcription)

        if os.path.exists(audio_path):
            os.remove(audio_path)

        return summary
    except Exception as e:
        print(f"❌ An error occurred: {e}")
        return None

# -------------------------------
# API Endpoints
# -------------------------------

@app.route('/summarize', methods=['POST'])
@login_required
def summarize():
    youtube_url = request.json.get('youtube_url')
    if not youtube_url:
        return jsonify({"error": "YouTube URL is required"}), 400

    summary = summarize_youtube_video(youtube_url)
    if summary:
        return jsonify({"summary": summary})
    else:
        return jsonify({"error": "Failed to summarize video"}), 500

@app.route('/ques')
@login_required
def serve_ques_page():
    return send_from_directory(app.static_folder, 'ques.html')

@app.route('/home')
@login_required
def serve_home_page():
    # Check if the user is logged in
    if current_user.is_authenticated:
        return send_from_directory(app.static_folder, 'home.html')
    return redirect(url_for('auth_form'))  # Redirect to login if not authenticated

@app.route('/auth')
def auth_form():
    return send_from_directory(app.static_folder, 'AuthForm.html')

@app.route('/')
def serve_landing_page():
    return send_from_directory(app.static_folder, 'landingPage.html')

@app.route('/api/quiz', methods=['GET'])
@login_required
def quiz():
    count = int(request.args.get("count", 5))
    file_path = "transcription.txt"
    quiz_data = generate_quiz(file_path, num_fill=count, num_mcq=count)
    return jsonify(quiz_data)

@app.route('/quiz/answers', methods=['POST'])
@login_required
def get_answers():
    data = request.get_json()
    file_path = "transcription.txt"
    count = int(data.get("count", 5))
    q_type = data.get("type", "both")

    quiz_data = generate_quiz(file_path, num_fill=count, num_mcq=count)
    answers = {}

    if "fill_in_the_blank" in quiz_data:
        answers["fill_in_the_blank"] = [q["answer"] for q in quiz_data["fill_in_the_blank"]]
    if "mcq" in quiz_data:
        answers["mcq"] = [q["answer"] for q in quiz_data["mcq"]]

    return jsonify(answers)

@app.route('/submit_score', methods=['POST'])
@login_required
def submit_score():
    data = request.get_json()
    score_value = int(data.get('score', 0))

    new_score = score(user_id=current_user.id, score=score_value, total_questions=10, question_type='mcq')
    try:
        db.session.add(new_score)
        db.session.commit()
        return jsonify({"message": "Score submitted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error saving score: {e}")
        return jsonify({"error": "Failed to submit score"}), 500

@app.route('/leaderboard', methods=['GET'])
@login_required
def leaderboard():
    top_scores = score.query.order_by(score.score.desc()).limit(10).all()
    result = []
    for s in top_scores:
        user = User.query.get(s.user_id)
        result.append({
            "email": user.email,
            "score": s.score,
            "timestamp": s.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        })
    return jsonify(result)

# -------------------------------
# Disable caching for back-button protection
# -------------------------------
@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# -------------------------------
# Run App
# -------------------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
