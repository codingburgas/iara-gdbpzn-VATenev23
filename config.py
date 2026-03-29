import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///database.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Weather API config
    WEATHER_API_KEY = os.environ.get('WEATHER_API_KEY') or '00000000000000000000000000000000'

    # Session config
    SESSION_PERMANENT = False
    SESSION_TYPE = 'filesystem'