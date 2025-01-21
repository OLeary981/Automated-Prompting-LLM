from app import db
from config import Config
from app.models import Story, Question, Model, Response, Prompt
import requests
import json
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

    return prompt.prompt_id

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

def call_LLM_GROQ(connection, story, question, story_id, question_id, model_name, model_id, temperature=0.5, max_tokens=1024, top_p=0.65):
    try:#
        # Ensure all parameters are of the correct type
        temperature = float(temperature)
        max_tokens = int(max_tokens)
        top_p = float(top_p)
        # max_tokens = int(max_tokens)
        # Send the prompt to Groq
        completion = groq_client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "user",
                    "content": f"Read my story: {story} now respond to these queries about it: {question}"
                }
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            stream=False,  # Indicate no streaming
            stop=None,
        )

        # Extract the response content from the completion object
        response_content = completion.choices[0].message.content

        # Print the response to the console
        print("Response from Groq LLM:")
        print(response_content)

        # Serialize the full response to JSON
        full_response_json = json.dumps(completion, default=lambda o: o.__dict__)

        # Insert prompt details into the prompt_tests table
        payload_json = json.dumps({
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
        })

        # Insert the response into the responses table
        save_prompt_and_response(connection, model_id, temperature, max_tokens, top_p, story_id, question_id, payload_json, response_content, full_response_json)

        return response_content

    except Exception as e:
        # Print an error message to the console
        print("Failed to get response from Groq LLM:")
        print(e)
        return None

def call_LLM_HF(story, question, model_name, temperature, max_tokens, top_p):
    # Example implementation of calling the LLM
    url = f"https://api.huggingface.co/models/{model_name}/generate"
    payload = {
        "story": story,
        "question": question,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "top_p": top_p
    }
    response = requests.post(url, json=payload)
    response_content = response.json().get("generated_text", "")

    # Insert the response into the responses table
    prompt = Prompt(model_id=model_id, temperature=temperature, max_tokens=max_tokens)
    db.session.add(prompt)
    db.session.commit()

    response_entry = Response(prompt_id=prompt.prompt_id, response_content=response_content)
    db.session.add(response_entry)
    db.session.commit()

    return response_content