from huggingface_hub import InferenceClient
import requests

print("Hello world v2")

API_URL = "https://api-inference.huggingface.co/models/meta-llama/Llama-3.2-1B"
headers = {"Authorization": "Bearer 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"}

def query(payload):
	response = requests.post(API_URL, headers=headers, json=payload)
	return response.json()
	
output = query({
	"inputs": "What colour is the sky?",
})

print(output)