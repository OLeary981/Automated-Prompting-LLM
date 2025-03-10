from app import db
from config import Config
from app.models import Story, Question, Model, Response, Prompt
import requests
import json
import time
from groq import Groq, APIError

GROQ_API_KEY = Config.GROQ_API_KEY
groq_client = Groq(api_key=GROQ_API_KEY)

def get_all_stories():
    return db.session.query(Story).all()

def get_all_questions():
    return db.session.query(Question).all()

def get_story_by_id(story_id):
    return db.session.query(Story).get(story_id)

def get_question_by_id(question_id):
    return db.session.query(Question).get(question_id)

def get_model_parameters_and_values(model_id):
    model = db.session.query(Model).get(model_id)
    parameters = json.loads(model.parameters)
        # Convert the list of parameters to a dictionary
    parameters_dict = {param['name']: param for param in parameters['parameters']}
    return parameters_dict

def get_model_name_by_id(model_id):
    model = db.session.query(Model).get(model_id)
    return model.name

def get_model_by_id(model_id):
    model = db.session.query(Model).get(model_id)
    model.parameters = json.loads(model.parameters)  # Parse JSON string into dictionary
    # Convert the list of parameters to a dictionary
    model.parameters = {param['name']: param for param in model.parameters['parameters']}
    return model


def get_provider_name_by_model_id(model_id):
    model = db.session.query(Model).get(model_id)
    return model.provider.provider_name

def get_request_delay_by_model_id(model_id):
    model = db.session.query(Model).get(model_id)
    return model.request_delay

def save_prompt_and_response(model_id, temperature, max_tokens, top_p, story_id, question_id, payload_json, response_content, full_response_json):
    """Save the prompt and response to the database."""
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

    response_entry = Response(
        prompt_id=prompt.prompt_id,
        response_content=response_content,
        full_response=full_response_json
    )
    db.session.add(response_entry)
    db.session.commit()

    return response_entry.response_id

# def call_LLM_GROQ(story, question, story_id, question_id, model_name, model_id, temperature, max_tokens, top_p):
#     # Example implementation of calling the LLM
#     url = f"https://api.groq.com/models/{model_name}/generate"
#     payload = {
#         "story": story,
#         "question": question,
#         "temperature": temperature,
#         "max_tokens": max_tokens,
#         "top_p": top_p
#     }
#     response = requests.post(url, json=payload)
#     response_content = response.json().get("generated_text", "")
#     full_response_json = response.json()

#     # Save the prompt and response to the database
#     save_prompt_and_response(
#         model_id=model_id,
#         temperature=temperature,
#         max_tokens=max_tokens,
#         top_p=top_p,
#         story_id=story_id,
#         question_id=question_id,
#         payload_json=json.dumps(payload),
#         response_content=response_content,
#         full_response_json=json.dumps(full_response_json)
#     )

#     return response_content

def call_llm(provider_name, story, question, story_id, question_id, model_name, model_id, **parameters):
    if provider_name == "groq":
        return call_LLM_GROQ(story, question, story_id, question_id, model_name, model_id, **parameters)
    elif provider_name == "hf":
        return call_LLM_HF(story, question, story_id, question_id, model_name, model_id, **parameters)
    else:
        raise ValueError(f"Unknown provider: {provider_name}")

def prepare_and_call_llm(request, session):
    print("You've reached call LLM let's look at what is in the session")
    print(session)
    model_id = session.get('model_id')
    story_ids = session.get('story_ids', [])  # Handle multiple stories
    question_id = session.get('question_id')
    
    if not story_ids:
        return {"error": "No stories selected."}
    
    question = get_question_by_id(question_id).content
    model_name = get_model_name_by_id(model_id)
    provider_name = get_provider_name_by_model_id(model_id)
    request_delay = get_request_delay_by_model_id(model_id)  # Delay in seconds

    # Extract and convert parameters dynamically
    parameters = {}
    for param, details in get_model_parameters_and_values(model_id).items():
        if details['type'] == 'float':
            parameters[param] = float(request.form.get(param, 0.5))
        else:
            parameters[param] = int(request.form.get(param, 1024))

    responses = {}
    response_ids = []

    for i, story_id in enumerate(story_ids):
        story = get_story_by_id(story_id).content
        response = call_llm(provider_name, story, question, story_id, question_id, model_name, model_id, **parameters)
        print(response)

        if response:
            responses[story_id] = response
            response_ids.append(response['response_id'])
        else:
            responses[story_id] = {"error": "Failed to get response"}

        # Delay before the next request (if there are multiple)
        if i < len(story_ids) - 1:
            time.sleep(request_delay)

    session['response_ids'] = response_ids  # Store all response_ids in the session

    return responses


def call_LLM_GROQ(story, question, story_id, question_id, model_name, model_id, **parameters):
    try:
        # Set default values if parameters are not provided
        temperature = float(parameters.get('temperature', 0.5))
        max_tokens = int(parameters.get('max_tokens', 1024))
        top_p = float(parameters.get('top_p', 0.65))
        print("About to call LLM_Groq")

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

        # Print the response to the console
        print("Response from Groq LLM:")
        print(response_content)

        # Serialize the full response to JSON
        full_response_json = json.dumps(completion, default=lambda o: o.__dict__)

        # Insert prompt details into the prompt_tests table
        payload_json = json.dumps(payload)

        # Insert the response into the responses table
        response_id = save_prompt_and_response(model_id, temperature, max_tokens, top_p, story_id, question_id, payload_json, response_content, full_response_json)
        

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

def call_LLM_HF(story, question, story_id, question_id, model_name, model_id, **parameters):
    # Set default values if parameters are not provided
    temperature = float(parameters.get('temperature', 0.5))
    max_tokens = int(parameters.get('max_tokens', 1024))
    top_p = float(parameters.get('top_p', 0.65))

    # Prepare the payload with all parameters
    payload = {
        "story": story,
        "question": question,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "top_p": top_p
    }

    # Add any additional parameters to the payload
    for key, value in parameters.items():
        if key not in payload:
            payload[key] = value

    # Example implementation of calling the LLM
    url = f"https://api.huggingface.co/models/{model_name}/generate"
    response = requests.post(url, json=payload)
    response_content = response.json().get("generated_text", "")
    full_response_json = response.json()

    # Save the prompt and response to the database
    save_prompt_and_response(
        model_id=model_id,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
        story_id=story_id,
        question_id=question_id,
        payload_json=json.dumps(payload),
        response_content=response_content,
        full_response_json=json.dumps(full_response_json)
    )

    return response_content