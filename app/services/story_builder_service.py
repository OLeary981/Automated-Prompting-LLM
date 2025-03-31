import itertools
import re
import time
from app import db
from app.models import Template, Story, Question, Word, Field
import llm as llm

def get_all_templates():
    return db.session.query(Template).all()

def generate_stories(template_id, field_data=None):
    """Generate stories based on template and field data."""
    generated_stories_ids = []
    try:
        template = db.session.query(Template).get(template_id)
        if not template:
            raise ValueError(f"Template with ID {template_id} not found")
            
        # Pass the field data to the template_filler
        generated_stories_ids = template_filler(template, template_id, field_data)
        
    except Exception as e:
        print(f"Error in generate_stories: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
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

def template_filler(template, template_id, field_data=None):
    """Fill the template with permutations of field values."""
    fields, missing_fields = get_template_fields(template_id)
    
    # If field_data is provided from the form, use it to fill in missing fields
    if field_data:
        print(f"Using field data from form: {field_data}")
        # Use field_data for all fields (both existing and missing)
        for field in list(fields.keys()) + missing_fields:
            if field in field_data and field_data[field]:
                fields[field] = field_data[field]
                print(f"Setting field '{field}' with values: {field_data[field]}")
            elif field in missing_fields:
                # If a field is missing and not in field_data, use a default
                fields[field] = ["[No value provided]"]
                print(f"No value for missing field '{field}', using default")
    else:
        # This is for command-line usage - keep it for testing
        if missing_fields:
            for field in missing_fields:
                user_input = input(f"No sample data available for field '{field}'. Enter values (comma-separated): ")
                fields[field] = [value.strip() for value in user_input.split(',')] if user_input else ["default"]

    # Generate all permutations
    permutations = generate_permutations(fields)
    print(f"Generated {len(permutations)} permutations")

    generated_stories_ids = []
    for permutation in permutations:
        story_content = template.content
        for field, value in zip(fields.keys(), permutation):
            story_content = story_content.replace(f"{{{field}}}", value)

        # Create and save the new story
        new_story = Story(content=story_content, template_id=template_id)
        db.session.add(new_story)
        db.session.commit()  # Commit after each story to get the ID
        generated_stories_ids.append(new_story.story_id)

    print(f"Created {len(generated_stories_ids)} stories")
    return generated_stories_ids

def update_field_words(field_data):
    """Update field words based on user selection"""
    for field_name, words in field_data.items():
        # Get or create the field
        field = db.session.query(Field).filter_by(field=field_name).first()
        if not field:
            field = Field(field=field_name)
            db.session.add(field)
            db.session.commit()
        
        # Clear existing relationships
        field.words = []
        
        # Add selected words
        for word in words:
            existing_word = db.session.query(Word).filter_by(word=word).first()
            if not existing_word:
                new_word = Word(word=word)
                field.words.append(new_word)
                db.session.add(new_word)
            else:
                field.words.append(existing_word)
        
        db.session.commit()
    return True

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