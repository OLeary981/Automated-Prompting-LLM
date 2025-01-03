import os
import sqlite3

def connect(db_file="database.db"):
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
(1, 'llama3-groq-70b-8192-tool-use-preview', 1, 'placeholder', 5, 'temperature, max_tokens, top_p'),
(2, 'llama-3.1-70b-versatile', 1, 'placeholder', 5, 'temperature, max_tokens, top_p'),
(3, 'meta-llama/Llama-3.1-8B-Instruct', 2, 'placeholder', 5, 'temperature, max_tokens, top_p');
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

def delete_database(db_file):
    if os.path.exists(db_file):
        os.remove(db_file)
        print(f"Deleted {db_file}")
    else:
        print(f"{db_file} does not exist")

def add_story(connection, content, template_id=None):
    with connection:
        connection.execute("INSERT INTO story (content, template_id) VALUES (?, ?)", (content, template_id))
        
def add_template(connection, content):
    with connection:
        connection.execute("INSERT INTO template (content) VALUES (?)", (content,))
        
def add_category(connection, content):
    with connection:
        connection.execute("INSERT INTO category (category) VALUES (?)", (content,))

def add_question(connection, content):
    with connection:
        connection.execute("INSERT INTO question (content) VALUES (?)", (content,))

def add_prompt(connection, model_id, temperature, max_tokens, top_p, story_id, question_id, payload):
    with connection:
        cursor = connection.execute(
            "INSERT INTO prompt(model_id, temperature, max_tokens, top_p, story_id, question_id, payload) VALUES ( ?, ?, ?, ?, ?, ?, ?)",
            (model_id, temperature, max_tokens, top_p, story_id, question_id, payload)
        )
        return cursor.lastrowid

def add_response(connection, prompt_id, response_content, full_response):
    with connection:
        connection.execute("INSERT INTO response (prompt_id, response_content, full_response) VALUES (?, ?, ?)", (prompt_id, response_content, full_response))

        
def add_word_with_field(connection, word, field):
    with connection:
        # Insert the word if it does not exist
        connection.execute("INSERT OR IGNORE INTO word (word) VALUES (?)", (word,))
        
        # Insert the field if it does not exist
        connection.execute("INSERT OR IGNORE INTO field (field) VALUES (?)", (field,))
        
        # Get the word_id and field_id
        word_id = connection.execute("SELECT word_id FROM word WHERE word = ?", (word,)).fetchone()[0]
        field_id = connection.execute("SELECT field_id FROM field WHERE field = ?", (field,)).fetchone()[0]
        
        # Insert the word-field relationship if it does not exist
        connection.execute("INSERT OR IGNORE INTO word_field (word_id, field_id) VALUES (?, ?)", (word_id, field_id))

def add_story_with_category(connection, story_content, category_name):
    with connection:
        # Insert the story if it does not exist
        connection.execute("INSERT OR IGNORE INTO story (content) VALUES (?)", (story_content,))
        
        # Insert the field if it does not exist
        connection.execute("INSERT OR IGNORE INTO field (category_name) VALUES (?)", (category_name,))
        
        # Get the story_id and field_id
        story_id = connection.execute("SELECT story_id FROM story WHERE content = ?", (story_content,)).fetchone()[0]
        category_id = connection.execute("SELECT category_id FROM category WHERE category = ?", (category_name,)).fetchone()[0]
        
        # Insert the story-field relationship if it does not exist
        connection.execute("INSERT OR IGNORE INTO story_field (story_id, category_id) VALUES (?, ?)", (story_id, category_id))

def get_all_stories(connection):
    with connection:
        return connection.execute("SELECT * FROM story").fetchall()

def get_all_questions(connection):
    with connection:
        return connection.execute("SELECT * FROM question").fetchall()

def get_all_story_templates(connection):
    with connection:
        return connection.execute("SELECT * FROM template").fetchall()

def get_story_by_id(connection, story_id):
    """Retrieve a story by its ID."""
    cursor = connection.cursor()
    cursor.execute("SELECT content FROM story WHERE story_id = ?", (story_id,))
    result = cursor.fetchone()
    return result[0] if result else None

def get_question_by_id(connection, question_id):
    """Retrieve a question by its ID."""
    cursor = connection.cursor()
    cursor.execute("SELECT content FROM question WHERE question_id = ?", (question_id,))
    result = cursor.fetchone()
    return result[0] if result else None

def get_words_by_field(connection, field_name):
    """Retrieve words for a given field from the database."""
    cursor = connection.cursor()
    cursor.execute("""
        SELECT w.word
        FROM word w
        JOIN word_field wf ON w.word_id = wf.word_id
        JOIN field f ON wf.field_id = f.field_id
        WHERE f.field = ?
    """, (field_name,))
    return [row[0] for row in cursor.fetchall()]

def get_template_by_id(connection, template_id):
    """Retrieve a template by its ID."""
    cursor = connection.cursor()
    cursor.execute("SELECT content FROM template WHERE template_id = ?", (template_id,))
    result = cursor.fetchone()
    return result[0] if result else None

def get_models_with_providers(connection):
    """Retrieve the list of models along with their providers."""
    cursor = connection.cursor()
    cursor.execute("""
        SELECT model.model_id, model.name, provider.provider_name
        FROM model
        JOIN provider ON model.provider_id = provider.provider_id
    """)
    return cursor.fetchall()

def get_model_name_by_id(connection, model_id):
    """Retrieve the model name by its ID."""
    cursor = connection.cursor()
    cursor.execute("SELECT name FROM model WHERE model_id = ?", (model_id,))
    result = cursor.fetchone()
    return result[0] if result else None

def get_provider_name_by_model_id(connection, model_id):
    """Retrieve the provider name by the model ID."""
    cursor = connection.cursor()
    cursor.execute("""
        SELECT provider.provider_name
        FROM provider
        JOIN model ON provider.provider_id = model.provider_id
        WHERE model.model_id = ?
    """, (model_id,))
    result = cursor.fetchone()
    return result[0] if result else None

# Main execution
if __name__ == "__main__":
    db_file = "database.db"
    delete_database(db_file)
    connection = sqlite3.connect(db_file)
    create_tables(connection)
    print("Database set up, let's rock and roll")
    insert_initial_data(connection)

