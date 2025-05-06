from flask import Blueprint

# Create the main blueprint
llm_bp = Blueprint('llm', __name__, url_prefix='/llm')

# Import routes to register them with the blueprint
from . import routes