import textwrap
import database
from llm import call_LLM_GROQ

def prompt_add_story(connection):
    content = input("Enter story content: ")
    database.add_story(connection, content)
    print(f"Story '{content}' added.")

def prompt_see_all_stories(connection):
    stories = database.get_all_stories(connection)
    title = "DETAILS OF ALL STORIES"
    total_width = 90
    id_width = 5
    content_width = total_width - id_width - 10  # Adjust for ID width and separators

    print("*" * total_width)
    print(title.center(total_width))
    print("*" * total_width)

    for story in stories:
        story_id = story[0]
        content = story[1]
        wrapped_content = textwrap.wrap(content, width=content_width)

        # Print the first line with the ID
        print(f"| ID: {story_id:<{id_width}} | {wrapped_content[0].ljust(content_width)} |")
        
        # Print subsequent lines with an empty ID column
        for line in wrapped_content[1:]:
            print(f"| {'':<{id_width + 4}} | {line.ljust(content_width)} |")

        print("*" * total_width)  # Separator between stories

def prompt_add_question(connection):
    content = input("Enter question content: ")
    database.add_question(connection, content)
    print(f"Question '{content}' added.")

def prompt_see_all_questions(connection):
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

def prompt_create_and_send_db_prompt(connection):
    stories = database.get_all_stories(connection)
    questions = database.get_all_questions(connection)

    if not stories or not questions:
        print("No stories or questions available in the database.")
        return

    print("Available Stories:")
    for story in stories:
        print(f"ID: {story[0]}, Content: {story[1][:50]}...")  # Display first 50 characters

    story_id = int(input("Enter the ID of the story you want to use: "))

    print("Available Questions:")
    for question in questions:
        print(f"ID: {question[0]}, Content: {question[1][:50]}...")  # Display first 50 characters

    question_id = int(input("Enter the ID of the question you want to use: "))

    story = database.get_story_by_id(connection, story_id)
    question = database.get_question_by_id(connection, question_id)

    if not story or not question:
        print("Invalid story or question ID.")
        return

    # Explanation of parameters
    print("\nParameter Explanations:")
    print("1. Temperature (0.0 to 1.0): Controls the randomness of the output. Lower values make the output more deterministic (less random).")
    print("2. Max Tokens (1 to 2048): The maximum number of tokens to generate in the response.")
    print("3. Top P (0.0 to 1.0): Controls nucleus sampling. Only the tokens with the top cumulative probability are considered.\n")
    
    # Prompt the user for temperature, max_tokens, and top_p
    temperature = float(input("Enter temperature (e.g., 0.5): "))
    max_tokens = int(input("Enter max tokens (e.g., 1024): "))
    top_p = float(input("Enter top_p (e.g., 0.65): "))

    response = call_LLM_GROQ(story[1], question[1], temperature, max_tokens, top_p)
    print("Response from LLM:", response)

    # Insert into prompt_tests table
    prompt_test_id = database.add_prompt_test(connection, story_id, question_id)

    # Insert into responses table
    database.add_response(connection, prompt_test_id, response)
    print("Response saved to database.")