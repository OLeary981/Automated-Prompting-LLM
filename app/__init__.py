from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os

# Initialize the database
db = SQLAlchemy()

def create_app():
    # Create the Flask app
    app = Flask(__name__)

    # Load configuration from config.py
    app.config.from_object('config.Config')

    # Initialize the database with the app
    db.init_app(app)

    # Register routes
    from . import routes
    app.register_blueprint(routes.bp)

    return app