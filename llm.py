from config import GROQ_API_KEY, HUGGINGFACE_API_KEY
from huggingface_hub import InferenceClient
from groq import Groq  # Assuming you have a Groq client library

# Initialize clients
hf_client = InferenceClient(token=HUGGINGFACE_API_KEY)
groq_client = Groq(api_key=GROQ_API_KEY)

def call_LLM_GROQ(story, question):
    completion = groq_client.chat.completions.create(
        model="llama3-groq-70b-8192-tool-use-preview",
        messages=[
            {
                "role": "user",
                "content": "Read my story: " + story + " now respond to these queries about it: " + question
            }
        ],
        temperature=0.5,
        max_tokens=1024,
        top_p=0.65,
        stream=True,
        stop=None,
    )
    response_content = ""
    for chunk in completion:
        response_content += chunk.choices[0].delta.content or ""
    
    print("Response received from LLM")
    return response_content

def call_LLM_HF(messages, model="meta-llama/Llama-3.1-8B-Instruct", max_tokens=500):
    stream = hf_client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        stream=True
    )
    response_content = ""
    for chunk in stream:
        response_content += chunk.choices[0].delta.content or ""
    
    print("Response received from LLM")
    return response_content