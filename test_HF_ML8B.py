import os
from huggingface_hub import InferenceClient
from dotenv import load_dotenv

load_dotenv()
#This does not work as I need a pro subscription
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")

client = InferenceClient(token = HUGGINGFACE_API_KEY)

messages = [
	{ "role": "user", "content": "What is the capital of France?" }
]

stream = client.chat.completions.create(
    model="meta-llama/Llama-3.1-8B-Instruct", 
	messages=messages, 
	max_tokens=500,
	stream=True
)

for chunk in stream:
    print(chunk.choices[0].delta.content)