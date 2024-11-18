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
7) Import stories from CSV
8) Import questions from CSV
9) Exit

Your selection:
"""

MODEL_PROMPT = """
Please choose a model:
1) Groq - llama3-groq-70b-8192-tool-use-preview
2) Groq - llama-3.1-70b-versatile
3) Hugging Face - meta-llama/Llama-3.1-8B-Instruct

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
            model_input = input(MODEL_PROMPT)
            if model_input == "1":
                model = "llama3-groq-70b-8192-tool-use-preview"
                user_interaction.prompt_create_and_send_db_prompt(connection, model, "groq")
            elif model_input == "2":
                model = "llama-3.1-70b-versatile"
                user_interaction.prompt_create_and_send_db_prompt(connection, model, "groq")
            elif model_input == "3":
                model = "meta-llama/Llama-3.1-8B-Instruct"
                user_interaction.prompt_create_and_send_db_prompt(connection, model, "hf")
            else:
                print("Invalid model selection. Please try again.")
            time.sleep(1.5)
        elif user_input == "7":
            csv_file = input("Enter the path to the CSV file for stories: ")
            user_interaction.import_stories_from_csv(connection, csv_file)
        elif user_input == "8":
            csv_file = input("Enter the path to the CSV file for questions: ")
            user_interaction.import_questions_from_csv(connection, csv_file)
        elif user_input == "9":
            connection.close()
            print("Connection closed. Exiting the application.")
            break
        else:
            print("Invalid input. Please try again.")

if __name__ == "__main__":
    menu()