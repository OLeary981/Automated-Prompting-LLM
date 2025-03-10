import itertools
import re
import time
from app import db
from app.models import Template, Story, Question, Word, Field
import llm as llm

def get_all_templates():
    return db.session.query(Template).all()

def generate_stories(template_id):
    generated_stories_ids = []
    try:
        template = db.session.query(Template).get(template_id)
        generated_stories_ids = template_filler(template, template_id)
        print(generated_stories_ids)        
    finally:
        db.session.close()
    return generated_stories_ids

def get_template_fields(template_id):
    template = db.session.query(Template).get(template_id)
    field_names = re.findall(r'\{(.*?)\}', template.content)
    fields = {}
    missing_fields = []
    for field_name in field_names:
        field = db.session.query(Field).filter_by(field=field_name).first()
        if field:
            words = [word.word for word in field.words]
            fields[field_name] = words
        else:
            missing_fields.append(field_name)
    return fields, missing_fields

def add_words_to_field(field_name, new_words):
    field = db.session.query(Field).filter_by(field=field_name).first()
    if not field:
        field = Field(field=field_name)
        db.session.add(field)
        db.session.commit()
    words = [word.strip() for word in new_words.split(',')]
    for word in words:
        existing_word = db.session.query(Word).filter_by(word=word).first()
        if not existing_word:
            new_word = Word(word=word)
            field.words.append(new_word)
            db.session.add(new_word)
        else:
            if field not in existing_word.fields:
                existing_word.fields.append(field)
    db.session.commit()

def generate_permutations(fields):
    """Generate all possible permutations of field values."""
    field_names = list(fields.keys())
    return list(itertools.product(*(fields[field] for field in field_names)))

def template_filler(template, template_id):
    """Fill the template with permutations of field values."""
    fields, missing_fields = get_template_fields(template_id)  # Avoid redundant queries
    
    if missing_fields:
        for field in missing_fields:
            user_input = input(f"No sample data available for field '{field}'. Enter values (comma-separated): ")
            fields[field] = [value.strip() for value in user_input.split(',')] if user_input else ["default"]

    permutations = generate_permutations(fields)

    generated_stories_ids = []
    for permutation in permutations:
        story_content = template.content
        for field, value in zip(fields.keys(), permutation):
            story_content = story_content.replace(f"{{{field}}}", value)

        new_story = Story(content=story_content, template_id=template_id)
        db.session.add(new_story)
        db.session.commit()
        generated_stories_ids.append(new_story.story_id)

    return generated_stories_ids

# def send_stories_to_llm(story_ids):
#     if not story_ids:
#         print("No stories to send.")
#         return

#     send_to_llm = input("Do you want to send the generated stories to an LLM? (yes/no): ").strip().lower()
#     if send_to_llm != "yes":
#         return

#     model_prompt = input("Enter the model prompt: ")
#     selected_model_id = int(input(model_prompt))

#     # Retrieve model parameters and values
#     parameter_values = get_model_parameters_and_values(selected_model_id)

#     temperature = parameter_values["temperature"]
#     max_tokens = parameter_values["max_tokens"]
#     top_p = parameter_values["top_p"]

#     # Get the model and provider names
#     model_name = get_model_name_by_id(selected_model_id)
#     provider_name = get_provider_name_by_model_id(selected_model_id)
#     request_delay = get_request_delay_by_model_id(selected_model_id)
    
#     questions = db.session.query(Question).all()
#     print("Available Questions:")
#     for question in questions:
#         print(f"ID: {question.question_id}, Content: {question.content[:50]}...")  # Display first 50 characters

#     question_id = int(input("Enter the ID of the question you want to use: "))
#     question = db.session.query(Question).get(question_id).content.lstrip('\ufeff')

#     for story_id in story_ids:
#         story = db.session.query(Story).get(story_id).content.lstrip('\ufeff')
        
#         # Send the prompt to the appropriate LLM
#         if provider_name == "groq":
#             response = llm.call_LLM_GROQ(story, question, story_id, question_id, model_name, selected_model_id, temperature, max_tokens, top_p)
#         elif provider_name == "hf":
#             response = llm.call_LLM_HF(story, question, model_name, temperature, max_tokens, top_p)

#         print(f"Response for story ID {story_id}:")
#         print(response)

#         time.sleep(request_delay)

# def get_model_parameters_and_values(model_id):
#     # Placeholder function to retrieve model parameters and values
#     return {
#         "temperature": 0.7,
#         "max_tokens": 100,
#         "top_p": 0.9
#     }

# def get_model_name_by_id(model_id):
#     # Placeholder function to retrieve model name by ID
#     return "example_model"

# def get_provider_name_by_model_id(model_id):
#     # Placeholder function to retrieve provider name by model ID
#     return "groq"

# def get_request_delay_by_model_id(model_id):
#     # Placeholder function to retrieve request delay by model ID
#     return 1