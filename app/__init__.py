from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os
import json  # Add this import
import logging
import os

# Initialize the database
db = SQLAlchemy()



def configure_logging(app):
    """Set up logging for the application"""
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'app.log')
    
    # Create a file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    
    # Create a formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    
    # Add the handler to the root logger
    logging.getLogger().addHandler(file_handler)
    logging.getLogger().setLevel(logging.DEBUG)
    
    app.logger.info(f"Logging to {log_file}")

def create_app(config=None): 
    # Create the Flask app
    app = Flask(__name__, static_folder='static')
    
    # Load configuration from config.py
    app.config.from_object('config.Config')
    
    # Override with any provided config
    if config:
        app.config.update(config)
        
    # Initialize the database with the app
    db.init_app(app)
    
    # Register routes
    from .blueprints import register_blueprints
    register_blueprints(app)

    # Set up logging
    configure_logging(app)  

    # Initialize the async service ONLY ONCE, outside app context
    from .services import async_service
    async_service.init_async_service(app)

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

    @app.teardown_appcontext
    def cleanup_on_shutdown(exception=None):
        """Just log shutdown, don't restart services"""
        app.logger.info("App context shutting down")

    return app