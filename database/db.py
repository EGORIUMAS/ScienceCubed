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
    players = relationship("Player", back_populates="team")

class Player(Base):
    __tablename__ = 'players'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String)
    team_id = Column(Integer, ForeignKey('teams.id'))
    team = relationship("Team", back_populates="players")

class Question(Base):
    __tablename__ = 'questions'
    id = Column(Integer, primary_key=True)
    round_number = Column(Integer, nullable=False)
    text = Column(String, nullable=False)
    correct_answer = Column(String, nullable=False)
    options = Column(String)  # JSON string for round 2
    time_limit = Column(Integer, default=30)

class Answer(Base):
    __tablename__ = 'answers'
    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey('players.id'))
    question_id = Column(Integer, ForeignKey('questions.id'))
    answer_text = Column(String, nullable=False)
    is_correct = Column(Boolean)
    timestamp = Column(DateTime, default=datetime.utcnow)

def init_db(database_url):
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)