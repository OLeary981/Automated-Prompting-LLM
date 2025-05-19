import json

from flask import current_app, flash, redirect, render_template, request, url_for
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.blueprints.models import models_bp
from app.models import Model, Provider
from config import Config


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
            
            # Build parameters JSON
            parameters = []
            param_names = request.form.getlist('param_name[]')
            param_descriptions = request.form.getlist('param_description[]')
            param_types = request.form.getlist('param_type[]')
            param_defaults = request.form.getlist('param_default[]')
            param_min_values = request.form.getlist('param_min_value[]')
            param_max_values = request.form.getlist('param_max_value[]')
            
            for i in range(len(param_names)):
                if param_names[i]:  # Only add if name exists
                    parameters.append({
                        "name": param_names[i],
                        "description": param_descriptions[i],
                        "type": param_types[i],
                        "default": float(param_defaults[i]) if param_types[i] == 'float' else int(param_defaults[i]),
                        "min_value": float(param_min_values[i]) if param_types[i] == 'float' else int(param_min_values[i]),
                        "max_value": float(param_max_values[i]) if param_types[i] == 'float' else int(param_max_values[i])
                    })
            
            parameters_json = json.dumps({"parameters": parameters})
            
            # Create new model
            model = Model(
                name=name,
                provider_id=provider_id,
                endpoint=endpoint,
                request_delay=request_delay,
                parameters=parameters_json
            )
            
            db.session.add(model)
            db.session.commit()
            
            flash(f'Model "{name}" added successfully.', 'success')
            return redirect(url_for('models.list'))
            
        except (ValueError, TypeError) as e:
            flash(f'Invalid form data: {str(e)}', 'danger')
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'Database error: {str(e)}', 'danger')
    
    # GET request - show the form
    providers = Provider.query.all()
    return render_template('models/add.html', providers=providers)

@models_bp.route('/edit/<int:model_id>', methods=['GET', 'POST'])
def edit(model_id):
    """Edit an existing model."""
    model = Model.query.get_or_404(model_id)
    
    if request.method == 'POST':
        try:
            # Update model with form data
            model.name = request.form['name']
            model.provider_id = request.form['provider_id']
            model.endpoint = request.form.get('endpoint', '')
            model.request_delay = float(request.form.get('request_delay', 0))
            
            # Build parameters JSON - this stays the same
            parameters = []
            param_names = request.form.getlist('param_name[]')
            param_descriptions = request.form.getlist('param_description[]')
            param_types = request.form.getlist('param_type[]')
            param_defaults = request.form.getlist('param_default[]')
            param_min_values = request.form.getlist('param_min_value[]')
            param_max_values = request.form.getlist('param_max_value[]')
            
            for i in range(len(param_names)):
                if param_names[i]:  # Only add if name exists
                    param_value = param_defaults[i]
                    min_value = param_min_values[i]
                    max_value = param_max_values[i]
                    
                    # Convert to the right type
                    if param_types[i] == 'float':
                        param_value = float(param_value)
                        min_value = float(min_value)
                        max_value = float(max_value)
                    elif param_types[i] == 'integer':
                        param_value = int(param_value)
                        min_value = int(min_value)
                        max_value = int(max_value)
                    
                    parameters.append({
                        "name": param_names[i],
                        "description": param_descriptions[i],
                        "type": param_types[i],
                        "default": param_value,
                        "min_value": min_value,
                        "max_value": max_value
                    })
            
            model.parameters = json.dumps({"parameters": parameters})
            
            db.session.commit()
            flash(f'Model "{model.name}" updated successfully.', 'success')
            return redirect(url_for('models.list'))
            
        except (ValueError, TypeError) as e:
            flash(f'Invalid form data: {str(e)}', 'danger')
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'Database error: {str(e)}', 'danger')
    
    # GET request - show the edit form
    providers = Provider.query.all()
    
    # Parse the parameters JSON into a list for the template
    try:
        parameters_data = json.loads(model.parameters)
        parameters = parameters_data.get('parameters', [])
    except (json.JSONDecodeError, AttributeError):
        # If no parameters exist, create default ones
        parameters = []
        for name, param_config in Config.SYSTEM_DEFAULTS.items():
            parameters.append({
                "name": name,
                "description": param_config["description"],
                "type": param_config["type"],
                "default": param_config["default"],
                "min_value": param_config["min"],
                "max_value": param_config["max"]
            })
    
    # Enhance parameters with display information
    for param in parameters:
        param['display_min_max'] = param['type'] in ('float', 'integer')
    
    return render_template(
        'models/edit.html', 
        model=model, 
        providers=providers,
        parameters=parameters
    )





@models_bp.route('/providers')
def providers_list():
    """List all providers."""
    providers = Provider.query.all()
    return render_template('models/providers_list.html', providers=providers)

