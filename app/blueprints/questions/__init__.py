from flask import Blueprint

questions_bp = Blueprint('questions', __name__, url_prefix='/questions')

# Import routes to register them with the blueprint
from . import routes