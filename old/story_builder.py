import itertools
import data_access
import database
import re
import llm as llm
import time


def generate_stories(connection):
    generated_stories_ids = []
    data_access.prompt_see_all_templates(connection)
    template_id = int(input("Enter the number of the template you are selecting: "))
    template = database.get_template_by_id(connection, template_id)
    generated_stories_ids= template_filler(connection, template, template_id)
    print(generated_stories_ids)
    send_stories_to_llm(connection, generated_stories_ids)
    return generated_stories_ids


def template_filler(connection, template, template_id):
     # Extract the field names from the template
    field_names = re.findall(r'\{(.*?)\}', template)
    print(field_names)

    # Create a dictionary to map field names to their respective arrays
    fields = {}
    for field in field_names:
            words = database.get_words_by_field(connection, field)
            if words:
                fields[field] = words
            else:
                user_input = input(f"No sample data available for field '{field}'. Please enter values separated by commas: ")
                fields[field] = [value.strip() for value in user_input.split(',')] if user_input else ["default"]  # Use user input or default if input is empty
            print(f"Field: {field}, Words: {fields[field]}")

    # Generate all possible permutations
    permutations = list(itertools.product(*(fields[field] for field in field_names)))

    # Print the number of stories that will be generated
    print(f"Number of stories that will be generated: {len(permutations)}")

    # Replace the placeholders in the template with the permutations
    generated_stories_ids = []
    for permutation in permutations:
        story = template
        for field, value in zip(field_names, permutation):
            story = story.replace(f"{{{field}}}", value)
        print(story)
        story_id = database.add_story(connection, story, template_id)
        generated_stories_ids.append(story_id)
    return generated_stories_ids

def send_stories_to_llm(connection, story_ids):
    if not story_ids:
        print("No stories to send.")
        return

    send_to_llm = input("Do you want to send the generated stories to an LLM? (yes/no): ").strip().lower()
    if send_to_llm != "yes":
        return

    model_prompt = data_access.get_model_prompt(connection)
    selected_model_id = int(input(model_prompt))

    # Retrieve model parameters and values
    parameter_values = data_access.get_model_parameters_and_values(connection, selected_model_id)

    temperature = parameter_values["temperature"]
    max_tokens = parameter_values["max_tokens"]
    top_p = parameter_values["top_p"]

    # Get the model and provider names
    model_name = database.get_model_name_by_id(connection, selected_model_id)
    provider_name = database.get_provider_name_by_model_id(connection, selected_model_id)
    request_delay = database.get_request_delay_by_model_id(connection, selected_model_id)
    
    questions = database.get_all_questions(connection)
    print("Available Questions:")
    for question in questions:
        print(f"ID: {question[0]}, Content: {question[1][:50]}...")  # Display first 50 characters

    question_id = int(input("Enter the ID of the question you want to use: "))
    question = database.get_question_by_id(connection, question_id).lstrip('\ufeff')


    for story_id in story_ids:
        story = database.get_story_by_id(connection, story_id).lstrip('\ufeff')
        
        # Send the prompt to the appropriate LLM
        if provider_name == "groq":
            response = llm.call_LLM_GROQ(connection, story, question, story_id, question_id, model_name, selected_model_id, temperature, max_tokens, top_p)
        elif provider_name == "hf":
            response = llm.call_LLM_HF(story, question, model_name, temperature, max_tokens, top_p)

        print(f"Response for story ID {story_id}:")
        print(response)

        time.sleep(request_delay)