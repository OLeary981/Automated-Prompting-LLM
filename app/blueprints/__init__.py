# Import all blueprint objects
from .stories import stories_bp
from .templates import templates_bp
from .questions import questions_bp
from .llm import llm_bp
# from .story_builder import story_builder_bp
# from .categories import categories_bp
# from .llm_evaluation import llm_evaluation_bp
from .main import main_bp

def register_blueprints(app):
    """Register all blueprints with the Flask application"""
    app.register_blueprint(stories_bp)
    app.register_blueprint(templates_bp)
    app.register_blueprint(questions_bp)
    app.register_blueprint(llm_bp)
    # app.register_blueprint(story_builder_bp)
    # app.register_blueprint(llm_evaluation_bp)
    app.register_blueprint(main_bp)