import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the API keys from environment variables
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")