from flask import Flask, render_template
from flask_socketio import SocketIO

from config import DATABASE_URL
from database.db import Question, Team, GameState, init_db
import logging

Session = init_db(DATABASE_URL)

logger = logging.getLogger(__name__)

# Инициализируем socketio с gevent
socketio = SocketIO(async_mode='gevent')


def create_app(Session):
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config['SECRET_KEY'] = 'your_secret_key'  # Замените на реальный из config.py

    # Инициализируем socketio с app
    socketio.init_app(app)

    @app.route('/')
    def index():
        return render_template('index.html')

    # Обработчики Socket.IO
    @socketio.on('connect')
    def handle_connect():
        logger.info('Клиент подключен')
        # Можно добавить отправку текущего состояния

    return app

@socketio.on('connect')
def handle_connect():
    logger.info('Клиент подключен')
    # При подключении отправляем текущее состояние (если есть активный вопрос)
    session = Session()
    try:
        gs = session.query(GameState).first()
        if gs and gs.current_question_id:
            q = session.query(Question).get(gs.current_question_id)
            total_questions = session.query(Question).filter_by(round_number=gs.current_round).count() if gs.current_round else 0
            # Отправляем данные текущего вопроса
            socketio.emit('new_question', {
                'id': q.id,
                'text': q.text,
                'round': q.round_number,
                'options': q.options,
                'time_limit': q.time_limit
            })
            # Отправляем общее количество вопросов в раунде
            socketio.emit('game_info', {'total_questions': total_questions})
        else:
            # Нет активного вопроса — можно отправить таблицу лидеров / ожидание
            teams = session.query(Team).order_by(Team.score.desc()).all()
            teams_data = [{'id': t.id, 'name': t.name, 'score': t.score, 'answers': t.answers} for t in teams]
            socketio.emit('show_results', {'correct_answer': '', 'teams': teams_data})
    except Exception as e:
        logger.error(f"Error in handle_connect: {e}", exc_info=True)
    finally:
        session.close()


def start_web_server(app):
    socketio.run(app, host='0.0.0.0', port=5001, debug=True, use_reloader=False)