import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Configuration
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Database Configuration
DATABASE_URL = os.getenv('DATABASE_URL')

# Web Interface Configuration
SECRET_KEY = os.getenv('SECRET_KEY')
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')
TG_ADMIN_USERNAME = os.getenv('TG_ADMIN_USERNAME')

# Quiz Configuration
TEAMS_COUNT = 5
PLAYERS_PER_TEAM = 4
ROUNDS_COUNT = 3
TIME_PER_QUESTION = 30  # seconds