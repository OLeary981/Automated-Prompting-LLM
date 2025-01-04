import time
import database
import csv
import textwrap
import random
from groq import Groq
import os
from dotenv import load_dotenv
import user_interaction
import story_builder

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
5) Create and send a prompt from a manually entered story and question (not currently working)
6) Create and send a prompt from database stories and questions
7) Import stories from CSV
8) Import questions from CSV
9) Import templates from .txt
10) Import words with fields from CSV
11) See all templates
12) Generate stories from templates
13) Exit

Your selection:
"""


def get_model_prompt(connection):
    models = database.get_models_with_providers(connection)
    model_prompt = "Please choose a model:\n"
    for model in models:
        model_id, model_name, provider_name = model
        model_prompt += f"{model_id}) {provider_name} - {model_name}\n"
    model_prompt += "\nYour selection:\n"
    return model_prompt



def menu():
    connection = database.connect()
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
            model_prompt = get_model_prompt(connection)
            selected_model_id = input(model_prompt)
            user_interaction.prompt_create_and_send_db_prompt(connection, selected_model_id)           
            time.sleep(1.5)
        elif user_input == "7":
            csv_file = input("Enter the path to the CSV file for stories: ")
            user_interaction.import_stories_from_csv(connection, csv_file)
            time.sleep(1.5)
        elif user_input == "8":
            csv_file = input("Enter the path to the CSV file for questions: ")
            user_interaction.import_questions_from_csv(connection, csv_file)
            time.sleep(1.5)
        elif user_input == "9":
            txt_file = input("Enter the path to the txt file for templates: ")
            user_interaction.import_templates_from_txt(connection, txt_file)
            time.sleep(1.5)
        elif user_input == "10":
            csv_file = input("Enter the path to the CSV file for words and fields: ")
            user_interaction.import_words_and_fields_from_csv(connection, csv_file)
            time.sleep(1.5)
        elif user_input == "11":
            user_interaction.prompt_see_all_templates(connection)
            time.sleep(1.5)
        elif user_input == "12":
            story_builder.generate_stories(connection)
            time.sleep(1.5)
        elif user_input == "13":
            connection.close()
            print("Connection closed. Exiting the application.")
            break
        else:
            print("Invalid input. Please try again.")

if __name__ == "__main__":
    menu()