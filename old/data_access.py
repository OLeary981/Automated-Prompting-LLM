import textwrap
import database
from llm import call_LLM_GROQ
import llm as llm
import csv
import json
import textwrap

# def display_longtext_html(title, items, id_width=5, total_width=90):
#     """Return long text items formatted as HTML with a given title."""
#     content_width = total_width - id_width - 10  # Adjust for ID width and separators

#     html = []
#     html.append(f"<h2>{title}</h2>")
#     html.append("<table class='table table-striped table-bordered table-hover table-sm'>")
#     html.append("<thead><tr><th>ID</th><th>Content</th></tr></thead>")
#     html.append("<tbody>")

#     for item in items:
#         item_id = item[0]
#         content = item[1]
#         wrapped_content = textwrap.wrap(content, width=content_width)

#         # Print the first line with the ID
#         html.append(f"<tr><td rowspan='{len(wrapped_content)}'>{item_id}</td><td>{wrapped_content[0]}</td></tr>")
        
#         # Print subsequent lines with an empty ID column
#         for line in wrapped_content[1:]:
#             html.append(f"<tr><td>{line}</td></tr>")

#     html.append("</tbody>")
#     html.append("</table>")
#     return "\n".join(html)

def see_all_stories_for_HTML(connection):
    """Retrieve and return all stories as list of tuples."""
    stories = database.get_all_stories(connection)
    return stories

def import_words_and_fields_from_csv(connection, csv_file):
    with open(csv_file, newline='') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            word, field = row
            database.add_word_with_field(connection, word, field)
    print("Words and fields imported successfully.")

def import_templates_from_txt(connection, txt_file):
    with open(txt_file, 'r', encoding='utf-8-sig') as txtfile:
        for line in txtfile:
            template = line.strip()  # Remove any leading/trailing whitespace
            database.add_template(connection, template)
    print("Story templates imported successfully.")

def prompt_add_story(connection):
    content = input("Enter story content: ")
    database.add_story(connection, content)
    print(f"Story '{content}' added.")

def display_longtext(title, items, id_width=5, total_width=90):
    """Display long text items with a given title."""
    content_width = total_width - id_width - 10  # Adjust for ID width and separators

    print("*" * total_width)
    print(title.center(total_width))
    print("*" * total_width)

    for item in items:
        item_id = item[0]
        content = item[1]
        wrapped_content = textwrap.wrap(content, width=content_width)

        # Print the first line with the ID
        print(f"| ID: {item_id:<{id_width}} | {wrapped_content[0].ljust(content_width)} |")
        
        # Print subsequent lines with an empty ID column
        for line in wrapped_content[1:]:
            print(f"| {'':<{id_width + 4}} | {line.ljust(content_width)} |")

        print("*" * total_width)  # Separator between items

def prompt_see_all_stories(connection):
    """Retrieve and return all stories formatted as HTML."""
    stories = database.get_all_stories(connection)
    return display_longtext_html("DETAILS OF ALL STORIES", stories)
    
def prompt_see_all_templates(connection):
    """Retrieve and display all templates."""
    templates = database.get_all_story_templates(connection)
    display_longtext("DETAILS OF ALL STORIES", templates)
    
    
def prompt_add_question(connection):
    content = input("Enter question content: ")
    database.add_question(connection, content)
    print(f"Question '{content}' added.")

def prompt_see_all_questions(connection): # could return to this to look at separation of concerns and have separate display method
    questions = database.get_all_questions(connection)
    title = "DETAILS OF ALL QUESTIONS"
    total_width = 90
    id_width = 5
    content_width = total_width - id_width - 10  # Adjust for ID width and separators

    print("*" * total_width)
    print(title.center(total_width))
    print("*" * total_width)

    for question in questions:
        question_id = question[0]
        content = question[1]
        wrapped_content = textwrap.wrap(content, width=content_width)

        # Print the first line with the ID
        print(f"| ID: {question_id:<{id_width}} | {wrapped_content[0].ljust(content_width)} |")
        
        # Print subsequent lines with an empty ID column
        for line in wrapped_content[1:]:
            print(f"| {'':<{id_width + 4}} | {line.ljust(content_width)} |")

        print("*" * total_width)  # Separator between questions

def prompt_create_and_send_manual_prompt(connection):
    story_content = input("Enter story content: ")
    question_content = input("Enter question content: ")
    
    # Explanation of parameters
    print("\nParameter Explanations:")
    print("1. Temperature (0.0 to 1.0): Controls the randomness of the output. Lower values make the output more deterministic.")
    print("2. Max Tokens (1 to 2048): The maximum number of tokens to generate in the response.")
    print("3. Top P (0.0 to 1.0): Controls nucleus sampling. Only the tokens with the top cumulative probability are considered.\n")
    
    # Prompt the user for temperature, max_tokens, and top_p
    temperature = float(input("Enter temperature (e.g., 0.5): "))
    max_tokens = int(input("Enter max tokens (e.g., 1024): "))
    top_p = float(input("Enter top_p (e.g., 0.65): "))
    
    response = call_LLM_GROQ(story_content, question_content, temperature, max_tokens, top_p)
    print("Response from LLM:")
    print(response)
    # You can add code here to save the response to the database

def prompt_create_and_send_db_prompt(connection, model_id):
    stories = database.get_all_stories(connection)    
    questions = database.get_all_questions(connection) 

    if not stories or not questions:
            if not stories and not questions:
                print("No stories and questions available in the database.")
            elif not stories:
                print("No stories available in the database.")
            elif not questions:
                print("No questions available in the database.")

            while True:
                choice = input("Would you like to add a story, a question, or both? (story/question/both/none): ").strip().lower()
                if choice == "story":
                    story_content = input("Enter the story content: ")
                    database.add_story(connection, story_content, None)  # Assuming template_id is not required here
                    stories = database.get_all_stories(connection)
                    break
                elif choice == "question":
                    question_content = input("Enter the question content: ")
                    database.add_question(connection, question_content)
                    questions = database.get_all_questions(connection)
                    break
                elif choice == "both":
                    story_content = input("Enter the story content: ")
                    database.add_story(connection, story_content, None)  # Assuming template_id is not required here
                    question_content = input("Enter the question content: ")
                    database.add_question(connection, question_content)
                    stories = database.get_all_stories(connection)
                    questions = database.get_all_questions(connection)
                    break
                elif choice == "none":
                    print("Operation cancelled.")
                    return
                else:
                    print("Invalid choice. Please enter 'story', 'question', 'both', or 'none'.")

    display_longtext("DETAILS OF ALL STORIES", stories)

    story_id = int(input("Enter the ID of the story you want to use: "))

    print("Available Questions:")
    for question in questions:
        print(f"ID: {question[0]}, Content: {question[1][:50]}...")  # Display first 50 characters

    question_id = int(input("Enter the ID of the question you want to use: "))

    story = database.get_story_by_id(connection, story_id).lstrip('\ufeff')
    question = database.get_question_by_id(connection, question_id).lstrip('\ufeff')

    parameter_values = get_model_parameters_and_values(connection, model_id)

    temperature = parameter_values["temperature"]
    max_tokens = parameter_values["max_tokens"]
    top_p = parameter_values["top_p"]

    
    # Get the model and provider names
    model_name = database.get_model_name_by_id(connection, model_id)
    provider_name = database.get_provider_name_by_model_id(connection, model_id)





    # Send the prompt to the appropriate LLM
    if provider_name == "groq":
        response = llm.call_LLM_GROQ(connection, story, question, story_id, question_id, model_name, model_id, temperature, max_tokens, top_p)
    elif provider_name == "hf":
        response = llm.call_LLM_HF(story[1], question[1], model, temperature, max_tokens, top_p)

   

def import_stories_from_csv(connection, csv_file):
    with open(csv_file, newline='', encoding='utf-8') as file:
        reader = csv.reader(file)
        for row in reader:
            if row:  # Ensure the row is not empty
                database.add_story(connection, row[0])
    print(f"Stories imported from {csv_file}")

def import_questions_from_csv(connection, csv_file):
    with open(csv_file, newline='', encoding='utf-8') as file:
        reader = csv.reader(file)
        for row in reader:
            if row:  # Ensure the row is not empty
                database.add_question(connection, row[0])
    print(f"Questions imported from {csv_file}")

def prompt_add_model(connection):
    """Prompt the user for model details and add the model to the database."""
    name = input("Enter model name: ")
    provider_id = int(input("Enter provider ID: "))
    endpoint = input("Enter endpoint: ")
    request_delay = int(input("Enter request delay: "))
    parameters = input("Enter parameters (comma-separated): ")
    
    database.add_model(connection, name, provider_id, endpoint, request_delay, parameters)
    print(f"Model '{name}' added successfully.")

def save_prompt_and_response(connection, model_id, temperature, max_tokens, top_p, story_id, question_id, payload_json, response_content, full_response_json):
    """Save the prompt and response to the database."""
    prompt_test_id = database.add_prompt(connection, model_id, temperature, max_tokens, top_p, story_id, question_id, payload_json)
    database.add_response(connection, prompt_test_id, response_content, full_response_json)
    return prompt_test_id

def get_model_prompt(connection):
    models = database.get_models_with_providers(connection)
    model_prompt = "Please choose a model:\n"
    for model in models:
        model_id, model_name, provider_name = model
        model_prompt += f"{model_id}) {provider_name} - {model_name}\n"
    model_prompt += "\nYour selection:\n"
    return model_prompt


def get_model_parameters_and_values(connection, model_id):
    """Retrieve model parameters and prompt the user for values."""
    parameters_json = database.get_model_parameters(connection, model_id)
    parameters = json.loads(parameters_json)["parameters"]

    print("\nModel Parameters:")
    for param in parameters:
        print(f"Name: {param['name']}")
        print(f"Description: {param['description']}")
        print(f"Type: {param['type']}")
        print(f"Default: {param['default']}")
        print(f"Min Value: {param['min_value']}")
        print(f"Max Value: {param['max_value']}")
        print()

    use_defaults = input("Do you want to use the default values for the parameters? (yes/no): ").strip().lower()

    if use_defaults == "yes":
        parameter_values = {param['name']: param['default'] for param in parameters}
    else:
        parameter_values = {}
        for param in parameters:
            while True:
                user_input = input(f"Enter value for {param['name']} (default: {param['default']}): ").strip()
                if user_input == "":
                    parameter_values[param['name']] = param['default']
                    break
                elif param['type'] == "float":
                    try:
                        value = float(user_input)
                        if param['min_value'] <= value <= param['max_value']:
                            parameter_values[param['name']] = value
                            break
                        else:
                            print(f"Value must be between {param['min_value']} and {param['max_value']}.")
                    except ValueError:
                        print("Invalid input. Please enter a float value.")
                elif param['type'] == "integer":
                    try:
                        value = int(user_input)
                        if param['min_value'] <= value <= param['max_value']:
                            parameter_values[param['name']] = value
                            break
                        else:
                            print(f"Value must be between {param['min_value']} and {param['max_value']}.")
                    except ValueError:
                        print("Invalid input. Please enter an integer value.")

    return parameter_values