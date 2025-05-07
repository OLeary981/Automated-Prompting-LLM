import importlib
import logging
from app import db
from app.models import Provider

logger = logging.getLogger(__name__)

class ProviderFactory:
    """Factory class to dynamically load and use LLM provider implementations"""
    
    @staticmethod
    def get_provider_instance(provider_name):
        """Get a specific provider implementation by name"""
        try:
            # Query database for provider details
            provider = db.session.query(Provider).filter_by(provider_name=provider_name).first()
            
            if not provider:
                logger.error(f"Provider '{provider_name}' not found in database")
                raise ValueError(f"Provider '{provider_name}' not found")
            
            # Import the provider module dynamically
            module_path = f"app.services.providers.{provider.module_name}"
            provider_module = importlib.import_module(module_path)
            
            # Get the provider class (convention: class name matches provider name with camel case)
            class_name = ''.join(word.capitalize() for word in provider.provider_name.split('_')) + 'Provider'
            provider_class = getattr(provider_module, class_name)
            
            # Instantiate provider with configuration
            config = {}
            if provider.config_json:
                config = json.loads(provider.config_json)
                
            return provider_class(config)
        
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to load provider '{provider_name}': {str(e)}")
            raise ValueError(f"Provider implementation not found: {str(e)}")
        except Exception as e:
            logger.error(f"Error initializing provider '{provider_name}': {str(e)}")
            raise