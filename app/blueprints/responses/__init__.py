from flask import Blueprint

responses_bp = Blueprint('responses', __name__, url_prefix='/responses')

# Import routes to register them with the blueprint
from . import routes