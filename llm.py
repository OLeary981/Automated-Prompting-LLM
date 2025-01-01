import os
import time
import requests
import json
import sqlite3
from dotenv import load_dotenv
from config import GROQ_API_KEY
from huggingface_hub import InferenceClient
from groq import Groq, APIError

import database  # Assuming you have a Groq client library

# Load environment variables from .env file
load_dotenv()

# Get the API key from environment variables
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
API_URL = "https://api-inference.huggingface.co/models/meta-llama/Llama-3.2-1B"
headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}

# Initialize clients
hf_client = InferenceClient(token=HUGGINGFACE_API_KEY) #not sure this works at the moment - not being used
groq_client = Groq(api_key=GROQ_API_KEY)

def query(payload, retries=3, delay=5):
    for attempt in range(retries):
        try:
            response = requests.post(API_URL, headers=headers, json=payload, timeout=10)
            response.raise_for_status()  # Raise an exception for HTTP errors
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                raise

def call_LLM_GROQ(connection, story, question, story_id, question_id, model, temperature=0.5, max_tokens=1024, top_p=0.65):
    try:
        # Send the prompt to Groq
        completion = groq_client.chat.completions.create(
            model=model,
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
            "model": model,
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
        prompt_test_id = database.add_prompt_test(connection, "groq", model, temperature, max_tokens, top_p, story_id, question_id, payload_json)
        database.add_response(connection, prompt_test_id, response_content, full_response_json)

        return response_content

    except APIError as e:
        # Print an error message to the console
        print("Failed to get response from Groq LLM:")
        print(e)
        return None


def call_LLM_HF(connection, story, question, model, story_id, question_id, temperature=0.5, max_tokens=1024, top_p=0.65):
    payload = {
        "inputs": f"{story}\n\n{question}",
        "parameters": {
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p
        }
    }
    payload_json = json.dumps(payload)

    # Insert prompt details into the prompt_tests table
    prompt_test_id = database.add_prompt_test(connection, "hf", model, temperature, max_tokens, top_p, story_id, question_id, payload_json)

    # Send the prompt to Hugging Face
    response = query(payload)
    response_content = response.get("generated_text", "")

    # Insert the response into the responses table
    database.add_response(connection, prompt_test_id, response_content)

    return response_content