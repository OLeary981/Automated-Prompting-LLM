import json
from groq import Groq, APIError
from .base_provider import BaseProvider

class GroqProvider(BaseProvider):
    """Provider implementation for Groq API"""
    
    def initialize_client(self):
        """Initialize the Groq client"""
        if not self.api_key:
            raise ValueError("Groq API key not found in configuration")
        return Groq(api_key=self.api_key)
    
    def get_request_payload(self, model_name, prompt_text, params):
        """Generate the Groq-specific request payload"""
        temperature = float(params.get('temperature', 0.5))
        max_tokens = int(params.get('max_tokens', 1024))
        top_p = float(params.get('top_p', 0.65))
        
        payload = {
            "model": model_name,
            "messages": [
                {
                    "role": "user",
                    "content": prompt_text
                }
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "stream": False
        }
        
        # Add any other parameters that might be in the params dict
        for key, value in params.items():
            if key not in ['temperature', 'max_tokens', 'top_p'] and key not in payload:
                payload[key] = value
                
        return payload
    
    def call_model(self, model_name, prompt_text, params):
        """Make a request to the Groq API"""
        try:
            payload = self.get_request_payload(model_name, prompt_text, params)
            completion = self.client.chat.completions.create(**payload)
            
            response_content = self.extract_response_content(completion)
            full_response_json = json.dumps(completion, default=lambda o: o.__dict__)
            
            return {
                "response_content": response_content,
                "full_response_json": full_response_json,
                "payload_json": json.dumps(payload)
            }
            
        except APIError as e:
            print(f"Groq API error: {e.status_code} - {e.json_body}")
            raise
        except Exception as e:
            print(f"Unexpected error calling Groq: {str(e)}")
            raise
    
    def extract_response_content(self, raw_response):
        """Extract the response content from Groq API response"""
        return raw_response.choices[0].message.content