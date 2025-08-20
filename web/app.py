from flask import Flask, render_template, request
from flask_socketio import SocketIO

from config import DATABASE_URL
from database.db import Question, Team, GameState, init_db
import logging

Session = init_db(DATABASE_URL)

logger = logging.getLogger(__name__)

# Initialize socketio with gevent
socketio = SocketIO(async_mode='gevent', cors_allowed_origins="*", logger=True, engineio_logger=True)


def create_app(Session):
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config['SECRET_KEY'] = 'your_secret_key'  # Replace with real secret from config.py

    # Initialize socketio with app
    socketio.init_app(app)

    @app.route('/')
    def index():
        return render_template('index.html')

    # Socket.IO handlers
    @socketio.on('connect')
    def handle_connect():
        logger.info(f'Client connected sid={request.sid}')
        session = Session()
        try:
            gs = session.query(GameState).first()
            if gs and gs.current_question_id:
                q = session.query(Question).get(gs.current_question_id)
                total_questions = session.query(Question).filter_by(
                    round_number=gs.current_round).count() if gs.current_round else 0
                logger.info(f"Sending current question to sid={request.sid} qid={q.id}")
                socketio.emit('new_question', {
                    'id': q.id,
                    'text': q.text,
                    'round': q.round_number,
                    'options': q.options,
                    'time_limit': q.time_limit
                }, namespace='/', to=request.sid)
                socketio.emit('game_info', {'total_questions': total_questions}, namespace='/', to=request.sid)
            else:
                # No active question - just show waiting screen without results
                logger.info(f"Sending waiting state to sid={request.sid}")
                # Don't send show_results here, just let the waiting screen show
                # Get total questions for the current round if available
                if gs and gs.current_round:
                    total_questions = session.query(Question).filter_by(
                        round_number=gs.current_round).count()
                    socketio.emit('game_info', {'total_questions': total_questions}, namespace='/', to=request.sid)
        except Exception as e:
            logger.error(f"Error in handle_connect: {e}", exc_info=True)
        finally:
            session.close()

    @socketio.on('client_ready')
    def handle_client_ready(data):
        logger.info(f"Client ready received from sid={request.sid} data={data}")

    # Test route: manually trigger emit to all clients
    @app.route('/emit_test')
    def emit_test():
        logger.info("Manual emit_test called — emitting test_event to all clients")
        socketio.emit('test_event', {'msg': 'hello from server'}, namespace='/')
        return "ok"

    return app


def start_web_server(app):
    socketio.run(app, host='0.0.0.0', port=5001, debug=True, use_reloader=False)