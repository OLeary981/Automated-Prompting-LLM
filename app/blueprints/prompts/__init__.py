from flask import Blueprint

prompts_bp = Blueprint('prompts', __name__, url_prefix='/prompts')

# Import routes to register them with the blueprint
from . import routes