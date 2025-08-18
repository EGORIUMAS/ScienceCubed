from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
from functools import wraps
import jwt
from datetime import datetime, timedelta
from database.db import Team, Question, init_db
from config import DATABASE_URL, SECRET_KEY, ADMIN_USERNAME, ADMIN_PASSWORD
import logging as logger
import json

# Настройка логирования
logger.basicConfig(level=logger.INFO)

Session = init_db(DATABASE_URL)

socketio = None

def create_app(db_session):
    global socketio
    app = Flask(__name__)
    app.config['SECRET_KEY'] = SECRET_KEY or 'your-secret-key'
    socketio = SocketIO(app)

    def token_required(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            token = request.headers.get('Authorization')
            if not token:
                logger.warning("Token is missing in request")
                return jsonify({'message': 'Token is missing!'}), 401
            try:
                data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
                logger.debug(f"Token decoded successfully: {data}")
            except Exception as e:
                logger.error(f"Invalid token: {str(e)}")
                return jsonify({'message': 'Token is invalid!'}), 401
            return f(*args, **kwargs)
        return decorated

    @app.route('/')
    def index():
        session = Session()
        try:
            teams = session.query(Team).all()
            current_question = session.query(Question).filter_by(current=True).first()

            initial_data = {
                'teams': [
                    {
                        'name': team.name,
                        'score': team.score or 0,
                        'id': team.id
                    }
                    for team in teams
                ],
                'currentQuestion': None
            }

            if current_question:
                initial_data['currentQuestion'] = {
                    'text': current_question.text,
                    'round': current_question.round_number,
                    'id': current_question.id,
                    'options': json.loads(current_question.options) if current_question.options else None,
                    'time_limit': current_question.time_limit
                }
                logger.debug(f"Current question loaded: {initial_data['currentQuestion']}")
            else:
                logger.debug("No current question found")

            logger.debug(f"Teams loaded: {initial_data['teams']}")
            return render_template('index.html', initial_data=initial_data)
        except Exception as e:
            logger.error(f"Error in index route: {str(e)}", exc_info=True)
            return jsonify({'error': 'Internal server error', 'message': str(e)}), 500
        finally:
            session.close()

    @app.route('/login', methods=['POST'])
    def login():
        auth = request.authorization
        if not auth:
            logger.warning("Missing credentials in login request")
            return jsonify({'message': 'Missing credentials'}), 401
        if not ADMIN_USERNAME or not ADMIN_PASSWORD:
            logger.error("Server configuration error: ADMIN_USERNAME or ADMIN_PASSWORD not set")
            return jsonify({'message': 'Server configuration error'}), 500
        if auth.username == ADMIN_USERNAME and auth.password == ADMIN_PASSWORD:
            token = jwt.encode({
                'user': auth.username,
                'exp': datetime.utcnow() + timedelta(hours=24)
            }, app.config['SECRET_KEY'], algorithm="HS256")
            logger.info(f"Login successful for user: {auth.username}")
            return jsonify({'token': token})
        logger.warning(f"Invalid credentials for user: {auth.username}")
        return jsonify({'message': 'Invalid credentials'}), 401

    @app.route('/api/questions', methods=['GET'])
    @token_required
    def get_questions():
        session = db_session()
        try:
            questions = session.query(Question).all()
            return jsonify([{
                'id': q.id,
                'text': q.text,
                'round': q.round_number,
                'correct_answer': q.correct_answer,
                'options': json.loads(q.options) if q.options else None,
                'time_limit': q.time_limit
            } for q in questions])
        finally:
            session.close()

    return app

def start_web_server(app):
    from gevent import pywsgi
    from geventwebsocket.handler import WebSocketHandler
    logger.info("Starting web server on port 5001")
    server = pywsgi.WSGIServer(('0.0.0.0', 5001), app, handler_class=WebSocketHandler)
    server.serve_forever()