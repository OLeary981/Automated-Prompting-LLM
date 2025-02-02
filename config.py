import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Secret key for session management and other security-related needs
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'

    # Database connection string
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(os.getcwd(), "instance", "database.db")}'
    #SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', f'sqlite:///{os.path.join(os.getcwd(), "instance", "database.db")}')
    #SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///instance/database.db'

    # Disable SQLAlchemy event system to save resources
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Other configuration options can be added here
    DEBUG = os.environ.get('FLASK_DEBUG') or True

    # API key for accessing the LLMs
    GROQ_API_KEY = os.environ.get('GROQ_API_KEY')