from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
from functools import wraps
import jwt
from datetime import datetime, timedelta
from database.db import Team, Question, init_db
from config import DATABASE_URL

Session = init_db(DATABASE_URL)


def create_app(db_session):
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your-secret-key'
    socketio = SocketIO(app)

    def token_required(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            token = request.headers.get('Authorization')

            if not token:
                return jsonify({'message': 'Token is missing!'}), 401

            try:
                data = jwt.decode(token, app.config['SECRET_KEY'])
            except:
                return jsonify({'message': 'Token is invalid!'}), 401

            return f(*args, **kwargs)

        return decorated

    @app.route('/')
    def index():
        session = Session()
        try:
            teams = session.query(Team).all()
            current_question = session.query(Question).order_by(Question.id.desc()).first()
            initial_data = {
                'teams': [{'name': team.name, 'score': team.score} for team in teams],
                'currentQuestion': {
                    'text': current_question.text,
                    'round': current_question.round_number
                } if current_question else None
            }
            return render_template('index.html', initial_data=initial_data)
        finally:
            session.close()

    @app.route('/login', methods=['POST'])
    def login():
        auth = request.authorization

        if auth and auth.username == 'admin' and auth.password == 'password':
            token = jwt.encode({
                'user': auth.username,
                'exp': datetime.utcnow() + timedelta(hours=24)
            }, app.config['SECRET_KEY'])

            return jsonify({'token': token})

        return jsonify({'message': 'Could not verify!'}), 401

    @app.route('/api/questions', methods=['GET'])
    @token_required
    def get_questions():
        questions = db_session.query(Question).all()
        return jsonify([{
            'id': q.id,
            'text': q.text,
            'round': q.round_number,
            'correct_answer': q.correct_answer
        } for q in questions])

    @socketio.on('start_question')
    def handle_start_question(data):
        question_id = data['question_id']
        emit('question_started', {'question_id': question_id}, broadcast=True)

    @socketio.on('timer_update')
    def handle_timer_update(data):
        emit('timer', data, broadcast=True)

    return app


def start_web_server(app):
    from gevent import pywsgi
    from geventwebsocket.handler import WebSocketHandler

    server = pywsgi.WSGIServer(('0.0.0.0', 5001), app, handler_class=WebSocketHandler)
    server.serve_forever()