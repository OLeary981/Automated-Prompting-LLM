import json
import os
from typing import Any, Dict, List, Optional

from flask import current_app
from groq import Groq
from sqlalchemy.exc import SQLAlchemyError

from app import db, session_scope
from app.models import Model, Provider
from config import Config


def get_all_models() -> List[Dict[str, Any]]:
    """
    Get all models from the database with their provider information and parameters.
    
    Returns:
        List of dictionaries containing complete model data
    """
    # Query models
    models = db.session.query(Model).all()
    
    # Convert to dictionaries to avoid detached instance errors
    result = []
    for model in models:
        # Get provider info
        provider = db.session.get(Provider, model.provider_id)
        provider_name = provider.provider_name if provider else "Unknown"
        
        # Parse parameters
        try:
            parameters_data = json.loads(model.parameters)
            parameters = parameters_data.get('parameters', [])
        except (json.JSONDecodeError, TypeError, AttributeError):
            parameters = []
        
        # Create a dictionary with all needed attributes
        model_dict = {
            'model_id': model.model_id,
            'name': model.name,
            'provider_id': model.provider_id,
            'provider': provider_name,
            'endpoint': model.endpoint,
            'request_delay': model.request_delay,
            'parameters': parameters,  # Include parsed parameters
            'raw_parameters': model.parameters  # Include raw JSON string 
        }
        result.append(model_dict)
    
    return result


def get_new_groq_models() -> List[Dict[str, Any]]:
    """
    Fetch available models from the Groq API, excluding any models already in the database.
    
    Returns:
        A list of model information dictionaries for models not yet in the database
    """
    try:
        # Get all existing model names from the database
        existing_model_names = {model.name for model in db.session.query(Model.name).all()}
        
        # Fetch models from Groq API
        client = Groq(
            api_key=os.environ.get("GROQ_API_KEY"),
        )
        models = client.models.list()
        
        # Filter out models that already exist in the database
        filtered_models = [
            model for model in models.data 
            if model.id not in existing_model_names
        ]
        
        return filtered_models
    except Exception as e:
        current_app.logger.error(f"Error fetching Groq models: {str(e)}")
        return []


def get_model_providers() -> List[Provider]:
    """
    Get all available model providers from the database.
    
    Returns:
        List of Provider objects
    """
    with session_scope() as session:
        return session.query(Provider).all()


def get_model_by_id(model_id: int) -> Optional[Model]:
    """
    Get a specific model by ID.
    
    Args:
        model_id: The ID of the model to retrieve
        
    Returns:
        The Model object or None if not found
    """
    with session_scope() as session:
        return session.query(Model).get(model_id)


def create_model(
    name: str, 
    provider_id: str, 
    endpoint: str, 
    request_delay: float,
    parameters: List[Dict[str, Any]]
) -> Model:
    """
    Create a new model in the database.
    
    Args:
        name: Model name
        provider_id: Provider ID
        endpoint: API endpoint URL
        request_delay: Delay between requests
        parameters: List of parameter configurations
        
    Returns:
        The newly created Model object
        
    Raises:
        ValueError: If validation fails
        SQLAlchemyError: If database operation fails
    """
    parameters_json = json.dumps({"parameters": parameters})
    
    with session_scope() as session:
        model = Model(
            name=name,
            provider_id=provider_id,
            endpoint=endpoint,
            request_delay=request_delay,
            parameters=parameters_json
        )
        
        session.add(model)
        # The commit is handled by the session_scope context manager
        
        # Make sure to refresh the model to get database-generated values
        session.flush()
        session.refresh(model)
        
        return model


def update_model(
    model_id: int,
    name: str, 
    provider_id: str, 
    endpoint: str, 
    request_delay: float,
    parameters: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Update an existing model in the database.
    
    Args:
        model_id: ID of the model to update
        name: New model name
        provider_id: New provider ID
        endpoint: New API endpoint URL
        request_delay: New delay between requests
        parameters: New list of parameter configurations
        
    Returns:
        The id and the name of the updated model
        
    Raises:
        ValueError: If validation fails
        SQLAlchemyError: If database operation fails
    """
    parameters_json = json.dumps({"parameters": parameters})
    
    with session_scope() as session:
        model = session.query(Model).get(model_id)
        if not model:
            raise ValueError(f"Model with ID {model_id} not found")
            
        model.name = name
        model.provider_id = provider_id
        model.endpoint = endpoint
        model.request_delay = request_delay
        model.parameters = parameters_json
        
        # The commit is handled by the session_scope context manager
        model_name = model.name
        return {"id": model_id, "name": model_name}


def create_default_parameters() -> List[Dict[str, Any]]:
    """
    Create a list of default parameters based on system configuration.
    
    Returns:
        List of parameter dictionaries
    """
    parameters = []
    for name, param_config in Config.SYSTEM_DEFAULTS.items():
        parameters.append({
            "name": name,
            "description": param_config["description"],
            "type": param_config["type"],
            "default": param_config["default"],
            "min_value": param_config["min"],
            "max_value": param_config["max"],
            "display_min_max": param_config["type"] in ('float', 'integer')
        })
    return parameters


def parse_model_parameters(model: Model) -> List[Dict[str, Any]]:
    """
    Parse the parameters JSON from a model.
    
    Args:
        model: The Model object
        
    Returns:
        List of parameter dictionaries, or default parameters if parsing fails
    """
    try:
        parameters_data = json.loads(model.parameters)
        parameters = parameters_data.get('parameters', [])
        
        # Enhance parameters with display information
        for param in parameters:
            param['display_min_max'] = param['type'] in ('float', 'integer')
            
        return parameters
    except (json.JSONDecodeError, AttributeError):
        # Return default parameters if parsing fails
        return create_default_parameters()


def process_parameter_form_data(form_data) -> List[Dict[str, Any]]:
    """
    Process parameter form data from a request.
    
    Args:
        form_data: The form data from the request
        
    Returns:
        List of processed parameter dictionaries
    """
    parameters = []
    param_names = form_data.getlist('param_name[]')
    param_descriptions = form_data.getlist('param_description[]')
    param_types = form_data.getlist('param_type[]')
    param_defaults = form_data.getlist('param_default[]')
    param_min_values = form_data.getlist('param_min_value[]')
    param_max_values = form_data.getlist('param_max_value[]')
    
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
    
    return parameters


def ensure_groq_provider():
    """
    Ensure that the Groq provider exists in the database.
    """
    with session_scope() as session:
        provider = session.query(Provider).filter_by(provider_name="Groq").first()
        if not provider:
            provider = Provider(
                provider_name="Groq",
                api_type="rest",
                api_base="https://api.groq.com/openai/v1", 
                description="Provider for Groq LLM API"
            )
            session.add(provider)