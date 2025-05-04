from flask import Blueprint

stories_bp = Blueprint('stories', __name__, url_prefix='/stories')

# Import routes to register them with the blueprint
from . import routes
