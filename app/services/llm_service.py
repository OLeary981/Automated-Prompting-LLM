import copy
import json
import logging
import time

import requests
from flask_sse import sse
from groq import APIError, Groq

from app import db
from app.models import Model, Prompt, Provider, Question, Response, Story
from config import Config

logger = logging.getLogger(__name__)

GROQ_API_KEY = Config.GROQ_API_KEY
groq_client = Groq(api_key=GROQ_API_KEY)




def get_model_name_by_id(model_id):
    model = db.session.query(Model).get(model_id)
    return model.name

def get_all_models():
    """Get all models with their provider information"""
    return db.session.query(Model).join(Provider).all()

def get_models_by_provider(provider_id):
    """Get all models for a specific provider"""
    return db.session.query(Model).filter_by(provider_id=provider_id).all()

def get_model_by_id(model_id):
    """Get model by ID and return with original parameters preserved"""
    model = db.session.query(Model).get(model_id)
    if model:
        # Parse parameters but keep the original in model.parameters
        parsed = json.loads(model.parameters)
        # Make a deep copy to ensure we don't modify the original
        model.parsed_parameters = {param['name']: copy.deepcopy(param) for param in parsed['parameters']}
    return model

def get_model_parameters(model_id, saved_parameters=None):
    """Get model parameters with any saved values applied"""
    model = get_model_by_id(model_id)
    if not model:
        return {}        
    parameters = model.parsed_parameters  # Use parsed_parameters instead of parameters
    if saved_parameters:
        parameters = apply_saved_parameters(parameters, saved_parameters)        
    return parameters


def get_provider_name_by_model_id(model_id):
    model = db.session.query(Model).get(model_id)
    return model.provider.provider_name

def get_request_delay_by_model_id(model_id):
    model = db.session.query(Model).get(model_id)
    return model.request_delay




def apply_saved_parameters(model_parameters, saved_parameters):
    """Apply saved parameter values while respecting model constraints"""
    if not saved_parameters:
        return model_parameters
        
    # Create a copy to avoid modifying the original
    parameters = copy.deepcopy(model_parameters)
    
    # Apply saved values where available and valid
    for param_name, param_details in parameters.items():
        if param_name in saved_parameters:
            saved_value = saved_parameters[param_name]
            
            if param_details['type'] == 'float':
                try:
                    saved_value = float(saved_value)
                    if param_details['min_value'] <= saved_value <= param_details['max_value']:
                        param_details['default'] = saved_value
                except (ValueError, TypeError):
                    pass
                    
            elif param_details['type'] == 'int':
                try:
                    saved_value = int(saved_value)
                    if param_details['min_value'] <= saved_value <= param_details['max_value']:
                        param_details['default'] = saved_value
                except (ValueError, TypeError):
                    pass
    
    return parameters




def save_prompt_and_response(model_id, temperature, max_tokens, top_p, story_id, question_id, 
                            payload_json, response_content, full_response_json, prompt_id=None):
    """
    Save the prompt and response to the database.
    If prompt_id is provided, reuse that prompt instead of creating a new one.
    """
    logger.info(f"save_prompt_and_response received prompt_id: {prompt_id} (type: {type(prompt_id)})")

    # If no prompt_id is provided, create a new prompt
    if prompt_id is None:
        prompt = Prompt(
            model_id=model_id,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            story_id=story_id,
            question_id=question_id,
            payload=payload_json
        )
        db.session.add(prompt)
        db.session.commit()
        prompt_id = prompt.prompt_id
    else:
        # Ensure prompt_id is an integer
        prompt_id = int(prompt_id) if not isinstance(prompt_id, int) else prompt_id
    # Create a response linked to the prompt (either new or existing)
    response_entry = Response(
        prompt_id=prompt_id,
        response_content=response_content,
        full_response=full_response_json
    )
    db.session.add(response_entry)
    db.session.commit()

    return response_entry.response_id


def call_llm(provider_name, story, question, story_id, question_id, model_name, model_id, prompt_id=None, **parameters):
    """
    Call the language model with the given parameters.
    
    If prompt_id is provided, reuses that prompt instead of creating a new one.
    """
    logger.info(f"LLM call: {provider_name}/{model_name} with story_id={story_id}, question_id={question_id}")
    logger.info(f"Parameters: {parameters}")
    
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
        
        # Use the provider-specific function but with parameters from the existing prompt
        if provider_name == "groq":
            return call_LLM_GROQ(
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
        elif provider_name == "hf":
            return call_LLM_HF(
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
            raise ValueError(f"Unknown provider: {provider_name}")
    else:
        # Standard processing (your existing code) with prompt_id=None
        if provider_name == "groq":
            return call_LLM_GROQ(story, question, story_id, question_id, model_name, model_id, prompt_id=None, **parameters)
        elif provider_name == "hf":
            return call_LLM_HF(story, question, story_id, question_id, model_name, model_id, prompt_id=None, **parameters)
        else:
            raise ValueError(f"Unknown provider: {provider_name}")

# def prepare_and_call_llm(model_id, story_ids, question_id, parameters, progress_callback=None):
#     print("You've reached call LLM let's look at what is in the session")
#     print(model_id, story_ids, question_id, parameters)
    
#     if not story_ids:
#         return {"error": "No stories selected."}
    
#     question = get_question_by_id(question_id).content
#     model_name = get_model_name_by_id(model_id)
#     provider_name = get_provider_name_by_model_id(model_id)
#     request_delay = get_request_delay_by_model_id(model_id)  # Delay in seconds

#     responses = {}
#     response_ids = []
#     progress = 0
#     total_stories = len(story_ids)

#     for i, story_id in enumerate(story_ids):
#         story = get_story_by_id(story_id).content
#         response = call_llm(provider_name, story, question, story_id, question_id, model_name, model_id, **parameters)
#         print(response)

#         if response:
#             responses[story_id] = response
#             response_ids.append(response['response_id'])
#         else:
#             responses[story_id] = {"error": "Failed to get response"}

#         # Update progress
#         progress = int(((i + 1) / total_stories) * 100)
#         if progress_callback:
#             progress_callback(progress)

#         # Delay before the next request (if there are multiple)
#         if i < len(story_ids) - 1:
#             time.sleep(request_delay)

#     return responses

def call_LLM_GROQ(story, question, story_id, question_id, model_name, model_id, prompt_id=None, **parameters):
    try:
        print(f"call_LLM_GROQ received prompt_id: {prompt_id} (type: {type(prompt_id)})")
        # Set default values if parameters are not provided
        temperature = float(parameters.get('temperature', 0.5))
        max_tokens = int(parameters.get('max_tokens', 1024))
        top_p = float(parameters.get('top_p', 0.65))

        # Prepare the payload with all parameters
        payload = {
            "model": model_name,
            "messages": [
                {
                    "role": "user",
                    "content": f"Read my story: {story} now respond to these queries about it: {question}"
                }
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "stream": False,
            "stop": None
        }

        # Add any additional parameters to the payload
        for key, value in parameters.items():
            if key not in payload:
                payload[key] = value

        # Send the prompt to Groq
        completion = groq_client.chat.completions.create(**payload)

        # Extract the response content from the completion object
        response_content = completion.choices[0].message.content

        # Serialize the full response to JSON
        full_response_json = json.dumps(completion, default=lambda o: o.__dict__)

        # Insert prompt details into the prompt_tests table
        payload_json = json.dumps(payload)

        # Insert the response into the responses table, passing prompt_id
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
            prompt_id=prompt_id  # Pass the prompt_id
        )

        return {"response_id": response_id, "response": response_content}

    except APIError as e:
        # Print an error message to the console
        print("Failed to get response from Groq LLM:")
        print(f"Error code: {e.status_code} - {e.json_body}")
        return None

    except Exception as e:
        
        # Print an error message to the console
        print("An unexpected error occurred:")
        print(e)
        return None

def call_LLM_HF(story, question, story_id, question_id, model_name, model_id, prompt_id=None, **parameters):
    try:
        # Set default values if parameters are not provided
        temperature = float(parameters.get('temperature', 0.5))
        max_tokens = int(parameters.get('max_tokens', 1024))
        top_p = float(parameters.get('top_p', 0.65))

        # Prepare the payload with all parameters
        payload = {
            "inputs": f"Read my story: {story} now respond to these queries about it: {question}",
            "parameters": {
                "temperature": temperature,
                "max_new_tokens": max_tokens,
                "top_p": top_p
            }
        }

        # Add any additional parameters to the payload
        for key, value in parameters.items():
            if key not in ['temperature', 'max_tokens', 'top_p']:
                payload["parameters"][key] = value

        # Example implementation of calling the LLM
        url = f"https://api.huggingface.co/models/{model_name}/generate"
        headers = {"Authorization": f"Bearer {Config.HF_API_KEY}"}
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code != 200:
            print(f"HF API error: {response.status_code} - {response.text}")
            return None
            
        response_json = response.json()
        response_content = response_json.get("generated_text", "")
        full_response_json = json.dumps(response_json)

        # Save the prompt and response to the database, passing prompt_id
        response_id = save_prompt_and_response(
            model_id=model_id,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            story_id=story_id,
            question_id=question_id,
            payload_json=json.dumps(payload),
            response_content=response_content,
            full_response_json=full_response_json,
            prompt_id=prompt_id  # Pass the prompt_id
        )

        # Return both the response and its ID consistently - SAME FORMAT as Groq
        return {"response_id": response_id, "response": response_content}
        
    except Exception as e:
        print(f"Unexpected error calling HF: {str(e)}")
        import traceback
        traceback.print_exc()
        return None