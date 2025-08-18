from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime

Base = declarative_base()

class Team(Base):
    __tablename__ = 'teams'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    leader_id = Column(Integer, nullable=False)
    score = Column(Integer, default=0)
    players = Column(String, default="[]")
    answers = Column(String, default="[]")

class Question(Base):
    __tablename__ = 'questions'
    id = Column(Integer, primary_key=True)
    round_number = Column(Integer, nullable=False)
    text = Column(String, nullable=False)
    correct_answer = Column(String, nullable=False)
    options = Column(String)  # JSON string for round 2
    time_limit = Column(Integer, default=30)
    start_time = Column(Integer)
    current = Column(Boolean, default=False)

class Answer(Base):
    __tablename__ = 'answers'
    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey('teams.id'))
    question_id = Column(Integer, ForeignKey('questions.id'))
    answer_text = Column(String, nullable=False)
    is_correct = Column(Boolean)
    timestamp = Column(DateTime, default=datetime.utcnow)

class GameState(Base):
    __tablename__ = 'game_state'
    id = Column(Integer, primary_key=True)
    current_round = Column(Integer, default=0)
    current_question_id = Column(Integer, ForeignKey('questions.id'), nullable=True)

def init_db(database_url):
    # Добавляем параметры для SQLite: таймаут и сериализацию
    if database_url.startswith('sqlite'):
        engine = create_engine(database_url, connect_args={'timeout': 15, 'check_same_thread': False})
    else:
        engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)