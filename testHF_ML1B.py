import os
import time
import requests
from dotenv import load_dotenv

print("Hello world v2")

# Load environment variables from .env file
load_dotenv()

# Get the API key from environment variables
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
#API_URL = "https://api-inference.huggingface.co/models/meta-llama/Meta-Llama-3-8B"
#8B not available - too large for serverless API?
API_URL = "https://api-inference.huggingface.co/models/meta-llama/Llama-3.2-1B"
headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}

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

payload = {
    "inputs": "Mary had a little lamb",
    "parameters": {
        "temperature": 0.1,  # Adjust temperature for more focused responses
        "max_tokens": 150,    # Limit the length of the response
        "top_p": 0.65         # Adjust top_p for more coherent responses
    }
}

output = query(payload)

print(output)