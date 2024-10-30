import time
import database
import csv
import textwrap
from groq import Groq
GROQ_API_KEY = "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"

MENU_PROMPT = """
-- Automated LLM Prompting App --
Please choose one of these options:
1) Add a story
2) See all stories
3) Add a question
4) See all questions
5) Create and send a prompt from a manually entered story and question
6) Create and send a prompt from database stories and questions
7) Exit

Your selection:
"""

def menu():
    connection = database.connect()
    database.create_tables(connection)
    while (user_input := input(MENU_PROMPT)) != "7":
        if user_input == "1":
            prompt_add_story(connection)
            time.sleep(0.5)
        elif user_input == "2":
            prompt_see_all_stories(connection)
            time.sleep(1.5)
        elif user_input == "3":
            prompt_add_question(connection)
            time.sleep(1.5)
        elif user_input == "4":
            prompt_see_all_questions(connection)
            time.sleep(1.5)
        elif user_input == "5":
            prompt_create_and_send_manual_prompt(connection)
            time.sleep(1.5)
        elif user_input == "6":
            prompt_create_and_send_db_prompt(connection)
            time.sleep(1.5)
        else:
            print("Invalid input. Please try again.")
            
            
            
            
            
def prompt_add_story(connection):
    content = input("Enter story content: ")
    database.add_story(connection, content)
    print(f"Story '{content}' added.")

def prompt_see_all_stories(connection):
    stories = database.get_all_stories(connection)
    title = "DETAILS OF ALL STORIES"
    total_width = 90
    id_width = 5
    content_width = total_width - id_width - 5  # Adjust for ID width and separators

    print("*" * total_width)
    print(title.center(total_width))
    print("*" * total_width)

    for story in stories:
        story_id = story[0]
        content = story[1]
        wrapped_content = textwrap.wrap(content, width=content_width)

        print(f"| {story_id:<{id_width}} | {wrapped_content[0].ljust(content_width)} |")
        for line in wrapped_content[1:]:
            print(f"| {'':<{id_width}} | {line.ljust(content_width)} |")

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
    content_width = total_width - id_width - 5  # Adjust for ID width and separators

    print("*" * total_width)
    print(title.center(total_width))
    print("*" * total_width)

    for question in questions:
        question_id = question[0]
        content = question[1]
        wrapped_content = textwrap.wrap(content, width=content_width)

        print(f"| {question_id:<{id_width}} | {wrapped_content[0].ljust(content_width)} |")
        for line in wrapped_content[1:]:
            print(f"| {'':<{id_width}} | {line.ljust(content_width)} |")

        print("*" * total_width)  # Separator between questions



def prompt_create_and_send_manual_prompt(connection):
    story_content = input("Enter story content: ")
    question_content = input("Enter question content: ")

    # Add story and question to the database
    database.add_story(connection, story_content)
    database.add_question(connection, question_content)

    # Get the story_id and question_id of the last inserted story and question
    story_id = connection.execute("SELECT last_insert_rowid();").fetchone()[0]
    question_id = connection.execute("SELECT last_insert_rowid();").fetchone()[0]

    # Create a prompt test with the story_id and question_id
    database.add_prompt_test(connection, story_id, question_id)

    print(f"Prompt created with story '{story_content}' and question '{question_content}'.")
    
    
    
    
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

    response = call_LLM_GROQ(story[1], question[1])
    print("Response from LLM:", response)

    # Insert into prompt_tests table
    prompt_test_id = database.add_prompt_test(connection, story_id, question_id)

    # Insert into responses table
    database.add_response(connection, prompt_test_id, response)
    print("Response saved to database.")
    
def call_LLM_GROQ(story, question):
    client = Groq(
        api_key=GROQ_API_KEY,
    )
    completion = client.chat.completions.create(
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


if __name__ == "__main__":
    menu()