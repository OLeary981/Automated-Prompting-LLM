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

    PER_PAGE = 10  # Number of items per page for pagination (NEED TO GO THROUGH ROUTES TO APPLY!)

    SYSTEM_DEFAULTS = {
    "temperature": {
        "default": 0.7,
        "min": 0.0,
        "max": 1.0,
        "type": "float",
        "description": "Controls randomness. Lower values make the output more deterministic, while higher values increase creativity."
    },
    "max_tokens": {
        "default": 1024,
        "min": 1,
        "max": 2048,
        "type": "integer",
        "description": "The maximum number of tokens to generate in the response."
    },
    "top_p": {
        "default": 0.8,
        "min": 0.0,
        "max": 1.0,
        "type": "float",
        "description": "Controls nucleus sampling, where the model considers only the most likely tokens with cumulative probability up to top_p."
    }
}