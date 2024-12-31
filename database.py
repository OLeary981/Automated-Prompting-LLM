import os
import sqlite3

CREATE_STORY_TABLE = """
CREATE TABLE IF NOT EXISTS story (
    story_id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL
);
"""

CREATE_QUESTION_TABLE = """
CREATE TABLE IF NOT EXISTS question (
    question_id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL
);
"""

CREATE_STORY_TEMPLATE_TABLE = """
CREATE TABLE IF NOT EXISTS story_template (
    story_template_id INTEGER PRIMARY KEY AUTOINCREMENT,
    template TEXT NOT NULL
);
"""

CREATE_PROMPT_TABLE = """
CREATE TABLE IF NOT EXISTS prompt (
    prompt_id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    temperature REAL NOT NULL,
    max_tokens INTEGER NOT NULL,
    top_p REAL NOT NULL,
    story_id INTEGER NOT NULL,
    question_id INTEGER NOT NULL,
    payload TEXT NOT NULL,    
    FOREIGN KEY (story_id) REFERENCES story(story_id),
    FOREIGN KEY (question_id) REFERENCES question(question_id)
);
"""

CREATE_RESPONSE_TABLE = """
CREATE TABLE IF NOT EXISTS response (
    response_id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_id INTEGER NOT NULL,
    response_content TEXT NOT NULL,
    full_response TEXT,
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

# Functions to create tables and add data
def create_tables(connection):
    with connection:
        connection.execute(CREATE_STORY_TABLE)
        connection.execute(CREATE_QUESTION_TABLE)
        connection.execute(CREATE_PROMPT_TABLE)
        connection.execute(CREATE_RESPONSE_TABLE)
        connection.execute(CREATE_STORY_TEMPLATE_TABLE)      
        connection.execute(CREATE_WORD_TABLE)
        connection.execute(CREATE_FIELD_TABLE)
        connection.execute(CREATE_WORD_FIELD_TABLE)

def insert_initial_data(connection):
    with connection:
        connection.executescript(INSERT_BASELINE_WORD)
        connection.executescript(INSERT_BASELINE_FIELD)
        connection.executescript(INSERT_WORD_FIELD)

def delete_database(db_file):
    if os.path.exists(db_file):
        os.remove(db_file)
        print(f"Deleted {db_file}")
    else:
        print(f"{db_file} does not exist")

def add_story(connection, content):
    with connection:
        connection.execute("INSERT INTO storY (content) VALUES (?)", (content,))

def add_question(connection, content):
    with connection:
        connection.execute("INSERT INTO question (content) VALUES (?)", (content,))

def add_prompt(connection, provider, model, temperature, max_tokens, top_p, story_id, question_id, payload):
    with connection:
        cursor = connection.execute(
            "INSERT INTO promptY(provider, model, temperature, max_tokens, top_p, story_id, question_id, payload) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (provider, model, temperature, max_tokens, top_p, story_id, question_id, payload)
        )
        return cursor.lastrowid

def add_response(connection, prompt_id, response_content, full_response):
    with connection:
        connection.execute("INSERT INTO responses (prompt_id, response_content, full_response) VALUES (?, ?, ?)", (prompt_id, response_content, full_response))
        
def add_word_with_field(connection, word, field):
    with connection:
        # Insert the word if it does not exist
        connection.execute("INSERT OR IGNORE INTO words (word) VALUES (?)", (word,))
        
        # Insert the field if it does not exist
        connection.execute("INSERT OR IGNORE INTO categories (field) VALUES (?)", (field,))
        
        # Get the word_id and field_id
        word_id = connection.execute("SELECT id FROM words WHERE word = ?", (word,)).fetchone()[0]
        field_id = connection.execute("SELECT id FROM categories WHERE field = ?", (field,)).fetchone()[0]
        
        # Insert the word-field relationship if it does not exist
        connection.execute("INSERT OR IGNORE INTO word_categories (word_id, field_id) VALUES (?, ?)", (word_id, field_id))

def get_all_stories(connection):
    with connection:
        return connection.execute("SELECT * FROM story").fetchall()

def get_all_questions(connection):
    with connection:
        return connection.execute("SELECT * FROM question").fetchall()

def get_all_story_templates(connection):
    with connection:
        return connection.execute("SELECT * FROM story_template").fetchall()

def get_story_by_id(connection, story_id):
    with connection:
        return connection.execute("SELECT * FROM story WHERE story_id = ?", (story_id,)).fetchone()

def get_question_by_id(connection, question_id):
    with connection:
        return connection.execute("SELECT * FROM question WHERE question_id = ?", (question_id,)).fetchone()

# Main execution
if __name__ == "__main__":
    db_file = "database.db"
    delete_database(db_file)
    connection = sqlite3.connect(db_file)
    create_tables(connection)
    insert_initial_data(connection)

