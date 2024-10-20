import datetime
from groq import Groq
GROQ_API_KEY = "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"

client = Groq(
    api_key = GROQ_API_KEY,
)

with open ('story.txt', 'r') as story_file:
    story_file = story_file.read()

with open ('questions.txt', 'r') as question_file:
    question_file = question_file.read()


completion = client.chat.completions.create(
    model="llama3-groq-70b-8192-tool-use-preview",
    messages=[
        {
            "role": "user",
            "content": "Read my story: " + story_file + "now respond to these queries about it: " + question_file
        }
    ],
    temperature=0.5,
    max_tokens=1024,
    top_p=0.65,
    stream=True,
    stop=None,
)

timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
output_file_name = f"story_response_{timestamp}.md"
with open(output_file_name, "w") as output_file:
    for chunk in completion:
        output_file.write(chunk.choices[0].delta.content or "")

# for chunk in completion:
#     print(chunk.choices[0].delta.content or "", end="")
