from flask import Blueprint

# Create the main blueprint
main_bp = Blueprint('main', __name__)

# Import routes to register them with the blueprint
from . import routes