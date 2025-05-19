from flask import current_app, flash, redirect, render_template, request, url_for
from sqlalchemy.exc import SQLAlchemyError

from app.blueprints.models import models_bp
from app.models.llm import Model, Provider
from app.services import models_service

# @models_bp.route('/list')
# def list():
#     """List all models with their providers."""
#     model_dicts = models_service.get_all_models()
#     # Convert the dictionaries back to Model-like objects
#     class ModelProxy:
#         """A simple proxy class that behaves like a Model object."""
#         def __init__(self, data):
#             for key, value in data.items():
#                 setattr(self, key, value)
    
#     # Convert each dictionary to a ModelProxy object
#     models = [ModelProxy(model_dict) for model_dict in model_dicts]
#     return render_template('models/list.html', models=models)

@models_bp.route('/list')
def list():
    """List all models with their providers."""
    models = Model.query.all()
    return render_template('models/list.html', models=models)


@models_bp.route('/add', methods=['GET', 'POST'])
def add():
    """Add a new model."""
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form['name']
            provider_id = request.form['provider_id']
            endpoint = request.form.get('endpoint', '')
            request_delay = float(request.form.get('request_delay', 0))
            
            # Process parameters from form data
            parameters = models_service.process_parameter_form_data(request.form)
            
            # Create model
            model = models_service.create_model(
                name=name,
                provider_id=provider_id,
                endpoint=endpoint,
                request_delay=request_delay,
                parameters=parameters
            )
            
            flash(f'Model "{name}" added successfully.', 'success')
            return redirect(url_for('models.list'))
            
        except (ValueError, TypeError) as e:
            flash(f'Invalid form data: {str(e)}', 'danger')
        except SQLAlchemyError as e:
            flash(f'Database error: {str(e)}', 'danger')
    
    # GET request - show the form with default parameters
    #providers = models_service.get_model_providers()
    providers = Provider.query.all()
    parameters = models_service.create_default_parameters()
    groq_models = models_service.get_new_groq_models()
    
    return render_template(
        'models/add.html', 
        providers=providers, 
        parameters=parameters,
        groq_models=groq_models
    )


@models_bp.route('/edit/<int:model_id>', methods=['GET', 'POST'])
def edit(model_id):
    """Edit an existing model."""
    model = Model.query.get(model_id)
    
    if not model:
        flash('Model not found.', 'danger')
        return redirect(url_for('models.list'))
    
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form['name']
            provider_id = request.form['provider_id']
            endpoint = request.form.get('endpoint', '')
            request_delay = float(request.form.get('request_delay', 0))
            
            # Process parameters from form data
            parameters = models_service.process_parameter_form_data(request.form)
            
            # Update model
            updated_model = models_service.update_model(
                model_id=model_id,
                name=name,
                provider_id=provider_id,
                endpoint=endpoint,
                request_delay=request_delay,
                parameters=parameters
            )
            
            flash(f'Model "{updated_model.name}" updated successfully.', 'success')
            return redirect(url_for('models.list'))
            
        except (ValueError, TypeError) as e:
            flash(f'Invalid form data: {str(e)}', 'danger')
        except SQLAlchemyError as e:
            flash(f'Database error: {str(e)}', 'danger')
    
    # GET request - show the edit form
    providers = Provider.query.all()
    parameters = models_service.parse_model_parameters(model)
 
    return render_template(
        'models/edit.html', 
        model=model, 
        providers=providers,
        parameters=parameters,
        
    )


@models_bp.route('/providers')
def providers_list():
    """List all providers."""
    providers = models_service.get_model_providers()
    return render_template('models/providers_list.html', providers=providers)