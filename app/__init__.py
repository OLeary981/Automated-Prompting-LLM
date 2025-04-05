from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os

# Initialize the database
db = SQLAlchemy()

def create_app(config= None): #allowing the config to be passed programmatically (for threads? and testing?)
    # Create the Flask app
    app = Flask(__name__)

    # Load configuration from config.py
    app.config.from_object('config.Config')

      # Override with any provided config
    if config:
        app.config.update(config)



    # Initialize the database with the app
    db.init_app(app)

    # Register routes
    from . import routes
    app.register_blueprint(routes.bp)

    return app