import copy
import json
import logging
import time
from contextlib import contextmanager
from typing import Any, Dict, Optional

import requests
from flask_sse import sse
from groq import APIError, Groq
from sqlalchemy.orm import scoped_session, sessionmaker

from app import session_scope
from app.models import Model, Prompt, Provider, Question, Response, Story
from config import Config

logger = logging.getLogger(__name__)

GROQ_API_KEY = Config.GROQ_API_KEY
groq_client = Groq(api_key=GROQ_API_KEY)

SYSTEM_DEFAULTS = Config.SYSTEM_DEFAULTS





def get_model_name_by_id(model_id):
    with session_scope() as session:
        model = session.query(Model).get(model_id)
        return model.name if model else None

def get_all_models():
    with session_scope() as session:
        models = session.query(Model).join(Provider).all()
        return [
            {
                "id": model.model_id,
                "name": model.name,
                "provider": model.provider.provider_name
            }
            for model in models
        ]

def get_models_by_provider(provider_id):
    with session_scope() as session:
        models = session.query(Model).filter_by(provider_id=provider_id).all()
        return [
            {
                "id": model.model_id,
                "name": model.name,
                "provider": model.provider.provider_name
            }
            for model in models
        ]

def get_model_by_id(model_id):
    with session_scope() as session:
        model = session.query(Model).get(model_id)
        if model:
            parsed = json.loads(model.parameters)
            parsed_parameters = {param['name']: copy.deepcopy(param) for param in parsed['parameters']}
            return {
                "id": model.model_id,
                "name": model.name,
                "provider": model.provider.provider_name,
                "parsed_parameters": parsed_parameters
            }
        return None

def get_model_parameters(model_id, saved_parameters=None):
    model = get_model_by_id(model_id)
    if not model:
        return {}
    parameters = model["parsed_parameters"]
    if saved_parameters:
        parameters = apply_saved_parameters(parameters, saved_parameters)
    return parameters

def get_provider_name_by_model_id(model_id):
    with session_scope() as session:
        model = session.query(Model).get(model_id)
        return model.provider.provider_name if model else None

def get_request_delay_by_model_id(model_id):
    with session_scope() as session:
        model = session.query(Model).get(model_id)
        return model.request_delay if model else 0
    
def _get_param(name: str, provided: dict) -> Any:
    """
    Hybrid parameter resolver that prioritizes caller-supplied values.    
    Args:
        name: Parameter name to retrieve
        provided: Dictionary of provided parameters        
    
    Returns:
        Parameter value from provided dict, or from defaults if missing
        
    Logs a warning when falling back to defaults.
    """
       
    if name in provided:
        return provided[name]
    
    # Check if we have a system default before trying to use it
    if name not in SYSTEM_DEFAULTS:
        logger.error(f"Parameter {name} not found in provided dict or SYSTEM_DEFAULTS")
        raise KeyError(f"Parameter {name} not found")

    # Loud but non-fatal signal.
    logger.warning(
        "Parameter %s missing from request; "
        "falling back to SYSTEM_DEFAULTS[\"%s\"].default=%r",
        name, name, SYSTEM_DEFAULTS[name]["default"],
    )
    return SYSTEM_DEFAULTS[name]["default"]

def apply_saved_parameters(model_parameters, saved_parameters):
    if not saved_parameters:
        return model_parameters

    parameters = copy.deepcopy(model_parameters)
    for param_name, param_details in parameters.items():
        if param_name in saved_parameters:
            saved_value = saved_parameters[param_name]
            logger.info(f"Processing parameter '{param_name}': saved_value={saved_value} (type={type(saved_value)})")
            try:
                param_type = str(param_details['type']).lower()
                if param_type in ('float',):
                    saved_value = float(saved_value)
                elif param_type in ('int', 'integer'):
                    saved_value = int(saved_value)
                    #issue converting max tokens possibly due to type inconsistency - so making it all the ints for now
                    #Have to use "in" as can't compare a string to a tuple.
                    
                # Move this log AFTER conversion
                logger.info(f"Converted '{param_name}' to {saved_value} (type={type(saved_value)})")
                if param_details['min_value'] <= saved_value <= param_details['max_value']:
                    param_details['default'] = saved_value
                    logger.info(f"Set '{param_name}' default to {saved_value}")
                else:
                    logger.info(f"Value {saved_value} for '{param_name}' out of bounds ({param_details['min_value']}–{param_details['max_value']})")
            except (ValueError, TypeError):
                logger.info(f"Failed to convert '{param_name}' value '{saved_parameters[param_name]}' to {param_details['type']}")
    return parameters




def call_llm(provider_name, story, question, story_id, question_id, model_name, model_id, prompt_id=None, run_id = None, **parameters):
    logger.info(f"LLM call: {provider_name}/{model_name} with story_id={story_id}, question_id={question_id}")
    logger.info(f"Parameters: {parameters}")

    if prompt_id:
        with session_scope() as session:
            prompt_id = int(prompt_id) if not isinstance(prompt_id, int) else prompt_id
            prompt = session.query(Prompt).filter_by(prompt_id=prompt_id).first()
            if not prompt:
                raise ValueError(f"Prompt ID {prompt_id} not found")

            story = session.query(Story).get(prompt.story_id).content
            question = session.query(Question).get(prompt.question_id).content
            parameters = {
                'temperature': prompt.temperature,
                'max_tokens': prompt.max_tokens,
                'top_p': prompt.top_p
            }

        if provider_name == "groq":
            return call_LLM_GROQ(story, question, story_id, question_id, model_name, model_id, prompt_id=prompt_id, run_id=run_id, **parameters)
        elif provider_name == "hf":
            return call_LLM_HF(story, question, story_id, question_id, model_name, model_id, prompt_id=prompt_id, run_id=run_id, **parameters)
        else:
            raise ValueError(f"Unknown provider: {provider_name}")
    else:
        if provider_name == "groq":
            return call_LLM_GROQ(story, question, story_id, question_id, model_name, model_id, prompt_id=None, run_id = run_id, **parameters)
        elif provider_name == "hf":
            return call_LLM_HF(story, question, story_id, question_id, model_name, model_id, prompt_id=None, run_id = run_id, **parameters)
        else:
            raise ValueError(f"Unknown provider: {provider_name}")

def call_LLM_GROQ(story, question, story_id, question_id, model_name, model_id, prompt_id=None, run_id = None, **parameters):
    try:
        logger.info(f"In llm_service, call_llm_GROQ (line 280) check on model_id:{model_id}")
        temperature = float(_get_param("temperature", parameters))
        max_tokens  = int(_get_param("max_tokens",  parameters))
        top_p       = float(_get_param("top_p",      parameters))

        payload = {
            "model": model_name,
            "messages": [
                {"role": "user", "content": f"Read my story: {story} now respond to these queries about it: {question}"}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "stream": False,
            "stop": None
        }

        for key, value in parameters.items():
            if key not in payload:
                payload[key] = value

        completion = groq_client.chat.completions.create(**payload)
        response_content = completion.choices[0].message.content
        full_response_json = json.dumps(completion, default=lambda o: o.__dict__)
        payload_json = json.dumps(payload)

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
            prompt_id=prompt_id,
            run_id=run_id
        )

        return {"response_id": response_id, "response": response_content}

    except APIError as e:
        logger.error(f"Groq API Error: {e.status_code} - {e.json_body}")
        return None
    except Exception as e:
        logger.exception("Unexpected error in call_LLM_GROQ")
        return None

def call_LLM_HF(story, question, story_id, question_id, model_name, model_id, prompt_id=None, run_id = None, **parameters):
    try:
        temperature = float(_get_param("temperature", parameters))
        max_tokens  = int(_get_param("max_tokens",  parameters))
        top_p       = float(_get_param("top_p",      parameters))
        payload = {
            "inputs": f"Read my story: {story} now respond to these queries about it: {question}",
            "parameters": {
                "temperature": temperature,
                "max_new_tokens": max_tokens,
                "top_p": top_p
            }
        }

        for key, value in parameters.items():
            if key not in ['temperature', 'max_tokens', 'top_p']:
                payload["parameters"][key] = value

        url = f"https://api.huggingface.co/models/{model_name}/generate"
        headers = {"Authorization": f"Bearer {Config.HF_API_KEY}"}
        response = requests.post(url, headers=headers, json=payload)

        if response.status_code != 200:
            logger.error(f"HF API error: {response.status_code} - {response.text}")
            return None

        response_json = response.json()
        response_content = response_json.get("generated_text", "")
        full_response_json = json.dumps(response_json)

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
            prompt_id=prompt_id,
            run_id=run_id
        )

        return {"response_id": response_id, "response": response_content}

    except Exception as e:
        logger.exception("Unexpected error calling HF")
        return None



def save_prompt_and_response(model_id, temperature, max_tokens, top_p, story_id, question_id, 
                              payload_json, response_content, full_response_json, prompt_id=None, run_id=None):
    logger.info(f"save_prompt_and_response (line 218) received prompt_id: {prompt_id} (type: {type(prompt_id)})")
    with session_scope() as session:
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
            session.add(prompt)
            session.commit()
            prompt_id = prompt.prompt_id
            logger.info(f"save_prompt_and_response (line 233) just after new prompt added to database received prompt_id: {prompt_id} (type: {type(prompt_id)})")
        else:
            prompt_id = int(prompt_id) if not isinstance(prompt_id, int) else prompt_id
            logger.info(f"save_prompt_and_response (line 236) if using retrieved prompt_id: {prompt_id} (type: {type(prompt_id)})")
            logger.info(f"llm_service line 247 run_id: {run_id}")
        response_entry = Response(
            prompt_id=prompt_id,
            response_content=response_content,
            full_response=full_response_json,
            run_id=run_id,
        )
        session.add(response_entry)
        session.commit()
        return response_entry.response_id