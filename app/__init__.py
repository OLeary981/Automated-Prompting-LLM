import json
import logging
import os

from flask import Flask, render_template, session
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    except Exception:
        pass

def configure_logging(app):
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'app.log')

    root_logger = logging.getLogger()
    if not any(isinstance(h, logging.FileHandler) and getattr(h, 'baseFilename', None) == log_file for h in root_logger.handlers):
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    root_logger.setLevel(logging.DEBUG)
    app.logger.info(f"Logging to {log_file}")

def create_app(config=None):
    app = Flask(__name__, static_folder='static')
    app.config.from_object('config.Config')
    if config:
        app.config.update(config)

    # Init extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Register blueprints
    from .blueprints import register_blueprints
    register_blueprints(app)

    # Logging
    configure_logging(app)

    # Async setup
    from .services import async_service
    async_service.init_async_service(app)
    app.async_loop = async_service.get_event_loop()

    # Custom template filters
    @app.template_filter('fromjson')
    def from_json(value):
        if value:
            try:
                return json.loads(value)
            except:
                return {}
        return {}

    # App teardown
    @app.teardown_appcontext
    def cleanup_on_shutdown(exception=None):
        app.logger.debug("App context shutting down")

    # Error handling
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('404.html'), 404

    # Context processor
    @app.context_processor
    def inject_current_question_content():
        from app.services import question_service
        question_id = session.get('question_id')
        question_content = None
        if question_id:
            question = question_service.get_question_by_id(question_id)
            if question:
                question_content = question.content
        return dict(current_question_content=question_content)

    return app


# import json  # Add this import
# import logging
# import os

# from flask import Flask, render_template, session
# from flask_migrate import Migrate
# from flask_sqlalchemy import SQLAlchemy
# from sqlalchemy import event
# from sqlalchemy.engine import Engine

# # Initialize the database
# db = SQLAlchemy()


# # Enable SQLite foreign key constraints
# @event.listens_for(Engine, "connect")
# def set_sqlite_pragma(dbapi_connection, connection_record):
#     try:
#         cursor = dbapi_connection.cursor()
#         cursor.execute("PRAGMA foreign_keys=ON")
#         cursor.close()
#     except Exception:
#         pass

# def configure_logging(app):
#     log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
#     os.makedirs(log_dir, exist_ok=True)
#     log_file = os.path.join(log_dir, 'app.log')

#     # Prevent duplicate handlers
#     root_logger = logging.getLogger()
#     if not any(isinstance(h, logging.FileHandler) and getattr(h, 'baseFilename', None) == log_file for h in root_logger.handlers):
#         file_handler = logging.FileHandler(log_file)
#         file_handler.setLevel(logging.DEBUG)
#         formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#         file_handler.setFormatter(formatter)
#         root_logger.addHandler(file_handler)
#     root_logger.setLevel(logging.DEBUG)
#     app.logger.info(f"Logging to {log_file}")



# def create_app(config=None): 
#     # Create the Flask app
#     app = Flask(__name__, static_folder='static')
    
#     # Load configuration from config.py
#     app.config.from_object('config.Config')
    
#     # Override with any provided config
#     if config:
#         app.config.update(config)
        
#     # Initialize the database with the app
#     db.init_app(app)
#     migrate = Migrate(app, db) #grey as is a registration of migration not a function call
#     # Register routes
#     from .blueprints import register_blueprints
#     register_blueprints(app)

#     # Set up logging
#     configure_logging(app)  

#     # Initialize the async service ONLY ONCE, outside app context
#     from .services import async_service
#     async_service.init_async_service(app)
#     app.async_loop = async_service.get_event_loop() #coordinates async loops avoids duplications. can now use app.async_loop throughout the app

#     # Register template filters
#     @app.template_filter('fromjson')
#     def from_json(value):
#         """Convert a JSON string to a Python dictionary"""
#         if value:
#             try:
#                 return json.loads(value)
#             except:
#                 return {}
#         return {}

#     @app.teardown_appcontext
#     def cleanup_on_shutdown(exception=None):
#         """Just log shutdown, don't restart services"""
#         app.logger.debug("App context shutting down") #downgrading to debug as it was spamming

#     @app.errorhandler(404)
#     def not_found_error(error):
#         return render_template('404.html'), 404

    

#     @app.context_processor
#     def inject_current_question_content():
#         from app.services import (
#             question_service,  #had to move this down here to avoid circular import
#         )
#         question_id = session.get('question_id')
#         question_content = None
#         if question_id:
#             question = question_service.get_question_by_id(question_id)
#             if question:
#                 question_content = question.content
#         return dict(current_question_content=question_content)
    
#     return app
