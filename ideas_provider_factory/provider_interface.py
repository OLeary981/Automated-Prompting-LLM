from abc import ABC, abstractmethod

class BaseProvider(ABC):
    """Base abstract class that all LLM providers must implement"""
    
    def __init__(self, config=None):
        """Initialize provider with configuration"""
        self.config = config or {}
        self.api_key = self.config.get('api_key')
        self._client = None
    
    @abstractmethod
    def initialize_client(self):
        """Initialize the provider client/API connection"""
        pass
    
    @property
    def client(self):
        """Get the API client, initializing if needed"""
        if self._client is None:
            self._client = self.initialize_client()
        return self._client
    
    @abstractmethod
    def call_model(self, model_name, prompt_text, params):
        """Make a request to the provider's model"""
        pass
    
    @abstractmethod
    def get_request_payload(self, model_name, prompt_text, params):
        """Generate the request payload for the provider API"""
        pass
    
    @abstractmethod
    def extract_response_content(self, raw_response):
        """Extract the text content from the provider's response"""
        pass