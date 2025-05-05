from flask import Blueprint

templates_bp = Blueprint('templates', __name__, url_prefix='/templates')

# Import routes to register them with the blueprint
from . import routes

