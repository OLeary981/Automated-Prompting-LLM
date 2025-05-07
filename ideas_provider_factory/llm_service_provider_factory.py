from app import db
from config import Config
from app.models import Story, Question, Model, Response, Prompt, Provider
import requests
import json
import time
import copy
import logging
from .provider_factory import ProviderFactory

logger = logging.getLogger(__name__)

# Removed direct Groq import in favor of provider factory
# groq_client = Groq(api_key=GROQ_API_KEY)

# Keep your existing service methods...

def call_llm(provider_name, story, question, story_id, question_id, model_name, model_id, prompt_id=None, **parameters):
    """
    Call the language model with the given parameters.
    
    If prompt_id is provided, reuses that prompt instead of creating a new one.
    """
    # Check if this is a rerun from an existing prompt
    print(f"call_llm received prompt_id: {prompt_id} (type: {type(prompt_id)})")
    if prompt_id:
        # Get the existing prompt
        prompt_id = int(prompt_id) if not isinstance(prompt_id, int) else prompt_id
        prompt = db.session.query(Prompt).filter_by(prompt_id=prompt_id).first()
        if not prompt:
            raise ValueError(f"Prompt ID {prompt_id} not found")
        
        # Get associated story and question
        story = db.session.query(Story).get(prompt.story_id).content
        question = db.session.query(Question).get(prompt.question_id).content
        
        # Use the provider factory to get the appropriate provider
        return call_model_with_provider(
            provider_name, 
            story, 
            question, 
            story_id, 
            question_id, 
            model_name, 
            model_id,
            prompt_id=prompt_id,  # Pass prompt_id for reuse
            temperature=prompt.temperature,
            max_tokens=prompt.max_tokens,
            top_p=prompt.top_p
        )
    else:
        # Standard processing with prompt_id=None
        return call_model_with_provider(
            provider_name, 
            story, 
            question, 
            story_id, 
            question_id, 
            model_name, 
            model_id, 
            prompt_id=None, 
            **parameters
        )

def call_model_with_provider(provider_name, story, question, story_id, question_id, model_name, model_id, prompt_id=None, **parameters):
    """
    Use the provider factory to call the appropriate LLM provider
    """
    try:
        # Get provider instance using factory
        provider = ProviderFactory.get_provider_instance(provider_name)
        
        # Prepare the prompt text
        prompt_text = f"Read my story: {story} now respond to these queries about it: {question}"
        
        # Call the model via the provider
        result = provider.call_model(model_name, prompt_text, parameters)
        
        # Extract results
        response_content = result["response_content"]
        full_response_json = result["full_response_json"]
        payload_json = result["payload_json"]
        
        # Save the prompt and response
        temperature = float(parameters.get('temperature', 0.5))
        max_tokens = int(parameters.get('max_tokens', 1024))
        top_p = float(parameters.get('top_p', 0.65))
        
        response_id = save_prompt_and_response(
            model_id=model_id,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            story_id=story_id,
            question_id=question_id,
            payload_json=payload_json,
            response_content=response_content,
            full_response_json=full_response_json,
            prompt_id=prompt_id
        )
        
        return {"response_id": response_id, "response": response_content}
        
    except Exception as e:
        logger.error(f"Error calling model with {provider_name}: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

# You can remove the provider-specific methods (call_LLM_GROQ and call_LLM_HF)
# as they're now handled by the provider implementations

# Keep your existing methods for getting models, parameters, etc.