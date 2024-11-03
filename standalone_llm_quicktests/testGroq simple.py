import os
from dotenv import load_dotenv
import datetime
from groq import Groq


load_dotenv()

GROQ_API_KEY = os.getenv("GRO_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

completion = client.chat.completions.create(
    #model="llama3-groq-70b-8192-tool-use-preview",
    model="llama-3.1-70b-versatile",
    messages=[
         {
            "role": "system",
            "content": "You are an ordinary person."
        },
        {
            "role": "user",
            "content": "Mary had a little lamb.."
        }
    ],
    temperature=0.5,
    max_tokens=1024,
    top_p=0.65,
    stream=True,
    stop=None,
)


for chunk in completion:
    print(chunk.choices[0].delta.content or "", end="")
