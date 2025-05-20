import os
import sqlite3


def connect(db_file="instance/database.db"):
    """Create a database connection to the SQLite database specified by db_file."""
    connection = sqlite3.connect(db_file)
    return connection


CREATE_QUESTION_TABLE = """
CREATE TABLE IF NOT EXISTS question (
    question_id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL
);
"""

CREATE_TEMPLATE_TABLE = """
CREATE TABLE IF NOT EXISTS template (
    template_id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL
);
"""

CREATE_STORY_TABLE = """
CREATE TABLE IF NOT EXISTS story (
    story_id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    template_id INTEGER, 
    FOREIGN KEY (template_id) REFERENCES template (template_id)
);
"""

CREATE_CATEGORY_TABLE = """
CREATE TABLE IF NOT EXISTS category (
    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL
);
"""

CREATE_STORY_CATEGORY_TABLE = """
CREATE TABLE IF NOT EXISTS story_category (
    story_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    PRIMARY KEY (story_id, category_id),
    FOREIGN KEY (story_id) REFERENCES story (story_id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES category (category_id) ON DELETE CASCADE
);
"""
CREATE_PROVIDER_TABLE ="""
CREATE TABLE provider (
    provider_id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_name TEXT NOT NULL    
);
"""

CREATE_MODEL_TABLE = """
CREATE TABLE IF NOT EXISTS model (
    model_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    provider_id INTEGER NOT NULL,
    endpoint TEXT,
    request_delay REAL NOT NULL,
    parameters TEXT NOT NULL,
    FOREIGN KEY (provider_id) REFERENCES provider (provider_id)
);
"""

CREATE_PROMPT_TABLE = """
CREATE TABLE IF NOT EXISTS prompt (
    prompt_id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id INTEGER NOT NULL,
    temperature REAL,
    max_tokens INTEGER,
    top_p REAL,
    story_id INTEGER NOT NULL,
    question_id INTEGER NOT NULL,
    payload LONGTEXT NOT NULL,    
    FOREIGN KEY (story_id) REFERENCES story(story_id),
    FOREIGN KEY (question_id) REFERENCES question(question_id),
    FOREIGN KEY (model_id) REFERENCES model(model_id)
);
"""

CREATE_RESPONSE_TABLE = """
CREATE TABLE IF NOT EXISTS response (
    response_id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_id INTEGER NOT NULL,
    response_content TEXT NOT NULL,
    full_response LONGTEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    flagged_for_review BOOLEAN DEFAULT FALSE,
    review_notes TEXT,
    FOREIGN KEY (prompt_id) REFERENCES prompt(prompt_id)
);
"""

# Story generator section
CREATE_WORD_TABLE = """
CREATE TABLE IF NOT EXISTS word (
    word_id INTEGER PRIMARY KEY AUTOINCREMENT,
    word TEXT NOT NULL UNIQUE
);
"""

CREATE_FIELD_TABLE = """
CREATE TABLE IF NOT EXISTS field (
    field_id INTEGER PRIMARY KEY AUTOINCREMENT,
    field TEXT NOT NULL UNIQUE
);
"""

CREATE_WORD_FIELD_TABLE = """
CREATE TABLE IF NOT EXISTS word_field (
    word_id INTEGER NOT NULL,
    field_id INTEGER NOT NULL,
    PRIMARY KEY (word_id, field_id),
    FOREIGN KEY (word_id) REFERENCES word (word_id) ON DELETE CASCADE,
    FOREIGN KEY (field_id) REFERENCES field (field_id) ON DELETE CASCADE
);
"""

INSERT_BASELINE_WORD = """
INSERT OR IGNORE INTO word (word) VALUES 
('France'),
('Spain'),
('man'),
('dog'),
('cat'),
('ball'),
('hat'),
('shiny'),
('red'),
('running'),
('falling');
"""

INSERT_BASELINE_FIELD = """
INSERT INTO field (field) VALUES 
('country'),
('character'),
('object'),
('adjective'),
('verb');
"""

INSERT_WORD_FIELD = """
INSERT INTO word_field (word_id, field_id) VALUES
((SELECT word_id FROM word WHERE word = 'France'), (SELECT field_id FROM field WHERE field = 'country')),
((SELECT word_id FROM word WHERE word = 'Spain'), (SELECT field_id FROM field WHERE field = 'country')),
((SELECT word_id FROM word WHERE word = 'man'), (SELECT field_id FROM field WHERE field = 'character')),
((SELECT word_id FROM word WHERE word = 'dog'), (SELECT field_id FROM field WHERE field = 'character')),
((SELECT word_id FROM word WHERE word = 'cat'), (SELECT field_id FROM field WHERE field = 'character')),
((SELECT word_id FROM word WHERE word = 'ball'), (SELECT field_id FROM field WHERE field = 'object')),
((SELECT word_id FROM word WHERE word = 'hat'), (SELECT field_id FROM field WHERE field = 'object')),
((SELECT word_id FROM word WHERE word = 'running'), (SELECT field_id FROM field WHERE field = 'verb')),
((SELECT word_id FROM word WHERE word = 'falling'), (SELECT field_id FROM field WHERE field = 'verb'));
"""

INSERT_PROVIDER = """
INSERT INTO provider (provider_id, provider_name) VALUES
(1, 'groq'),
(2, 'huggingface');
"""

INSERT_MODEL = """
INSERT INTO model (model_id, name, provider_id, endpoint, request_delay, parameters) VALUES
(1, 'llama-3.3-70b-versatile', 1, 'placeholder', 2.5, '{  "parameters": [    {      "name": "temperature",      "description": "Controls the randomness of the output. Lower values make the output more deterministic, while higher values increase creativity.",      "type": "float",      "default": 0.7,      "min_value": 0.0,      "max_value": 1.0    },    {      "name": "max_tokens",      "description": "The maximum number of tokens to generate in the response.",      "type": "integer",      "default": 1024,      "min_value": 1,      "max_value": 2048    },    {      "name": "top_p",      "description": "Controls nucleus sampling, where the model considers only the most likely tokens with cumulative probability up to `top_p`.",      "type": "float",      "default": 0.8,      "min_value": 0.0,      "max_value": 1.0    }  ]}'),
(2, 'gemma2-9b-it', 1, 'placeholder', 2.5, '{  "parameters": [    {      "name": "temperature",      "description": "Controls the randomness of the output. Lower values make the output more deterministic, while higher values increase creativity.",      "type": "float",      "default": 0.7,      "min_value": 0.0,      "max_value": 1.0    },    {      "name": "max_tokens",      "description": "The maximum number of tokens to generate in the response.",      "type": "integer",      "default": 1024,      "min_value": 1,      "max_value": 2048    },    {      "name": "top_p",      "description": "Controls nucleus sampling, where the model considers only the most likely tokens with cumulative probability up to `top_p`.",      "type": "float",      "default": 0.8,      "min_value": 0.0,      "max_value": 1.0    }  ]}'),
(3, 'deepseek-r1-distill-llama-70b', 1, 'placeholder', 2.5, '{  "parameters": [    {      "name": "temperature",      "description": "Controls the randomness of the output. Lower values make the output more deterministic, while higher values increase creativity.",      "type": "float",      "default": 0.7,      "min_value": 0.0,      "max_value": 1.0    },    {      "name": "max_tokens",      "description": "The maximum number of tokens to generate in the response.",      "type": "integer",      "default": 1024,      "min_value": 1,      "max_value": 2048    },    {      "name": "top_p",      "description": "Controls nucleus sampling, where the model considers only the most likely tokens with cumulative probability up to `top_p`.",      "type": "float",      "default": 0.8,      "min_value": 0.0,      "max_value": 1.0    }  ]}');
"""
INSERT_STORIES = """
INSERT INTO story (content, template_id) VALUES
('Lena rushed out of the café, realizing too late that she had left her umbrella behind. Rain poured relentlessly, soaking her in seconds. When she turned back, the café door was locked, and through the window, she saw a stranger picking up her umbrella with a knowing smile.', NULL),
('David had a cat, Mittens, who had a habit of vanishing for hours, but this time, she was gone for days. Just as he was about to put up missing posters, he heard a soft meow from inside the closet. When he opened it, Mittens sat smugly atop his winter coats—right where he swore he had looked a dozen times.', NULL),
('Ella stepped into the elevator, pressing the button for the 10th floor. The man beside her pressed 11. When they reached the 10th, she hesitated, suddenly unsure—she lived on the 11th.', NULL);
"""

INSERT_QUESTIONS = """
INSERT INTO question (content) VALUES
('What do you think will happen next?'),
('Interpret this story.'),
('What are the themes in this story?');
"""

INSERT_TEMPLATE = """
INSERT INTO template (template_id, content) VALUES
(1, 'Once upon a time in {country}, there was a {character} who loved {object}. One day, while [verb]ing, they found something shiny and {adjective}.'),
(2, '{name}'s {number} friends came for dinner and shared {number} {food}.'),
(3, 'The walked into the {adjective} {place}. A {adjective} man walked up to them. "Give me your {object}s." he said.');
(4, 'The {animal} ate a {large_object} and became a {job_title}.')
"""
# Functions to create tables and add data
def create_tables(connection):
    with connection:
        connection.execute(CREATE_STORY_TABLE)
        connection.execute(CREATE_QUESTION_TABLE)
        connection.execute(CREATE_PROMPT_TABLE)
        connection.execute(CREATE_RESPONSE_TABLE)
        connection.execute(CREATE_TEMPLATE_TABLE)      
        connection.execute(CREATE_WORD_TABLE)
        connection.execute(CREATE_FIELD_TABLE)
        connection.execute(CREATE_WORD_FIELD_TABLE)
        connection.execute(CREATE_CATEGORY_TABLE)
        connection.execute(CREATE_STORY_CATEGORY_TABLE)
        connection.execute(CREATE_PROVIDER_TABLE)
        connection.execute(CREATE_MODEL_TABLE)
    

def insert_initial_data(connection):
    with connection:
        connection.executescript(INSERT_BASELINE_WORD)
        connection.executescript(INSERT_BASELINE_FIELD)
        connection.executescript(INSERT_WORD_FIELD)
        connection.executescript(INSERT_PROVIDER)
        connection.executescript(INSERT_MODEL)
        connection.executescript(INSERT_QUESTIONS)
        connection.executescript(INSERT_STORIES)
        connection.executescript(INSERT_TEMPLATE)

def delete_database(db_file):
    if os.path.exists(db_file):
        os.remove(db_file)
        print(f"Deleted {db_file}")
    else:
        print(f"{db_file} does not exist")



# Main execution
if __name__ == "__main__":
    db_file = "instance/database.db"
    delete_database(db_file)
    connection = sqlite3.connect(db_file)
    create_tables(connection)
    print("Database set up, let's rock and roll")
    insert_initial_data(connection)

