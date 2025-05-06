import json
import requests
from .base_provider import BaseProvider

class HfProvider(BaseProvider):
    """Provider implementation for Hugging Face Inference API"""
    
    def initialize_client(self):
        """Initialize client - for HF we just need the API key"""
        if not self.api_key:
            raise ValueError("Hugging Face API key not found in configuration")
        return {"api_key": self.api_key}
    
    def get_request_payload(self, model_name, prompt_text, params):
        """Generate the HF-specific request payload"""
        temperature = float(params.get('temperature', 0.5))
        max_tokens = int(params.get('max_tokens', 1024))
        top_p = float(params.get('top_p', 0.65))
        
        payload = {
            "inputs": prompt_text,
            "parameters": {
                "temperature": temperature,
                "max_new_tokens": max_tokens,
                "top_p": top_p
            }
        }
        
        # Add any other parameters to the payload parameters
        for key, value in params.items():
            if key not in ['temperature', 'max_tokens', 'top_p']:
                payload["parameters"][key] = value
                
        return payload
    
    def call_model(self, model_name, prompt_text, params):
        """Make a request to the Hugging Face Inference API"""
        try:
            payload = self.get_request_payload(model_name, prompt_text, params)
            
            url = f"https://api.huggingface.co/models/{model_name}/generate"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code != 200:
                raise Exception(f"HF API error: {response.status_code} - {response.text}")
                
            response_json = response.json()
            response_content = self.extract_response_content(response_json)
            
            return {
                "response_content": response_content,
                "full_response_json": json.dumps(response_json),
                "payload_json": json.dumps(payload)
            }
            
        except Exception as e:
            print(f"Unexpected error calling Hugging Face: {str(e)}")
            raise
    
    def extract_response_content(self, raw_response):
        """Extract the response content from HF API response"""
        return raw_response.get("generated_text", "")