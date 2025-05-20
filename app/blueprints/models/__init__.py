from flask import Blueprint

models_bp = Blueprint('models', __name__, url_prefix='/models')


from . import routes