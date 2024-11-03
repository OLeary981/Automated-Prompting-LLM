import time
import database
import csv
import textwrap
from groq import Groq
import os
from dotenv import load_dotenv
import user_interaction

# Load environment variables from .env file
load_dotenv()

# Get the API keys from environment variables
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")

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
    while True:
        user_input = input(MENU_PROMPT)
        if user_input == "1":
            user_interaction.prompt_add_story(connection)
            time.sleep(0.5)
        elif user_input == "2":
            user_interaction.prompt_see_all_stories(connection)
            time.sleep(1.5)
        elif user_input == "3":
            user_interaction.prompt_add_question(connection)
            time.sleep(0.5)
        elif user_input == "4":
            user_interaction.prompt_see_all_questions(connection)
            time.sleep(1.5)
        elif user_input == "5":
            user_interaction.prompt_create_and_send_manual_prompt(connection)
            time.sleep(1.5)
        elif user_input == "6":
            user_interaction.prompt_create_and_send_db_prompt(connection)
            time.sleep(1.5)
        elif user_input == "7":
            connection.close()
            print("Connection closed. Exiting the application.")
            break
        else:
            print("Invalid input. Please try again.")

if __name__ == "__main__":
    menu()