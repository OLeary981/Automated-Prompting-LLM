from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os
import json  # Add this import

# Initialize the database
db = SQLAlchemy()

def create_app(config=None): 
    # Create the Flask app
    app = Flask(__name__)

    # Load configuration from config.py
    app.config.from_object('config.Config')

    # Override with any provided config
    if config:
        app.config.update(config)

    # Initialize the database with the app
    db.init_app(app)

    # Register template filters
    @app.template_filter('fromjson')
    def from_json(value):
        """Convert a JSON string to a Python dictionary"""
        if value:
            try:
                return json.loads(value)
            except:
                return {}
        return {}

    # Register routes
    from . import routes
    app.register_blueprint(routes.bp)

    return app