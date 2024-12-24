import os
import sqlite3

CREATE_STORIES_TABLE = """
CREATE TABLE IF NOT EXISTS stories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL
);
"""

CREATE_QUESTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL
);
"""

CREATE_STORY_TEMPLATES_TABLE = """
CREATE TABLE IF NOT EXISTS story_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template TEXT NOT NULL
);
"""

# CREATE_ADJECTIVES_TABLE = """
# CREATE TABLE IF NOT EXISTS adjectives (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     adjective TEXT NOT NULL
# );
# """

# CREATE_NOUNS_TABLE = """
# CREATE TABLE IF NOT EXISTS nouns (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     noun TEXT NOT NULL
# );
# """

CREATE_PROMPT_TESTS_TABLE = """
CREATE TABLE IF NOT EXISTS prompt_tests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    temperature REAL NOT NULL,
    max_tokens INTEGER NOT NULL,
    top_p REAL NOT NULL,
    story_id INTEGER NOT NULL,
    question_id INTEGER NOT NULL,
    payload TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (story_id) REFERENCES stories(id),
    FOREIGN KEY (question_id) REFERENCES questions(id)
);
"""

CREATE_RESPONSES_TABLE = """
CREATE TABLE IF NOT EXISTS responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_test_id INTEGER NOT NULL,
    response_content TEXT NOT NULL,
    full_response TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prompt_test_id) REFERENCES prompt_tests(id)
);
"""

# Story generator section
CREATE_WORDS_TABLE = """
CREATE TABLE IF NOT EXISTS words (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word TEXT NOT NULL UNIQUE
);
"""

CREATE_CATEGORIES_TABLE = """
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_name TEXT NOT NULL UNIQUE
);
"""

CREATE_WORD_CATEGORIES_TABLE = """
CREATE TABLE IF NOT EXISTS word_categories (
    word_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    PRIMARY KEY (word_id, category_id),
    FOREIGN KEY (word_id) REFERENCES words (id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE CASCADE
);
"""

INSERT_WORDS = """
INSERT INTO words (word) VALUES 
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

INSERT_CATEGORIES = """
INSERT INTO categories (category_name) VALUES 
('country'),
('character'),
('object'),
('adjective'),
('verb');
"""

INSERT_WORD_CATEGORIES = """
INSERT INTO word_categories (word_id, category_id) VALUES
((SELECT id FROM words WHERE word = 'France'), (SELECT id FROM categories WHERE category_name = 'country')),
((SELECT id FROM words WHERE word = 'Spain'), (SELECT id FROM categories WHERE category_name = 'country')),
((SELECT id FROM words WHERE word = 'man'), (SELECT id FROM categories WHERE category_name = 'character')),
((SELECT id FROM words WHERE word = 'dog'), (SELECT id FROM categories WHERE category_name = 'character')),
((SELECT id FROM words WHERE word = 'cat'), (SELECT id FROM categories WHERE category_name = 'character')),
((SELECT id FROM words WHERE word = 'ball'), (SELECT id FROM categories WHERE category_name = 'object')),
((SELECT id FROM words WHERE word = 'hat'), (SELECT id FROM categories WHERE category_name = 'object')),
((SELECT id FROM words WHERE word = 'running'), (SELECT id FROM categories WHERE category_name = 'verb')),
((SELECT id FROM words WHERE word = 'falling'), (SELECT id FROM categories WHERE category_name = 'verb'));
"""

# Functions to create tables and add data
def create_tables(connection):
    with connection:
        connection.execute(CREATE_STORIES_TABLE)
        connection.execute(CREATE_QUESTIONS_TABLE)
        connection.execute(CREATE_PROMPT_TESTS_TABLE)
        connection.execute(CREATE_RESPONSES_TABLE)
        connection.execute(CREATE_STORY_TEMPLATES_TABLE)
        #connection.execute(CREATE_ADJECTIVES_TABLE)
        #connection.execute(CREATE_NOUNS_TABLE)
        connection.execute(CREATE_WORDS_TABLE)
        connection.execute(CREATE_CATEGORIES_TABLE)
        connection.execute(CREATE_WORD_CATEGORIES_TABLE)

def insert_initial_data(connection):
    with connection:
        connection.executescript(INSERT_WORDS)
        connection.executescript(INSERT_CATEGORIES)
        connection.executescript(INSERT_WORD_CATEGORIES)

def delete_database(db_file):
    if os.path.exists(db_file):
        os.remove(db_file)
        print(f"Deleted {db_file}")
    else:
        print(f"{db_file} does not exist")

def add_story(connection, content):
    with connection:
        connection.execute("INSERT INTO stories (content) VALUES (?)", (content,))

def add_question(connection, content):
    with connection:
        connection.execute("INSERT INTO questions (content) VALUES (?)", (content,))

def add_prompt_test(connection, provider, model, temperature, max_tokens, top_p, story_id, question_id, payload):
    with connection:
        cursor = connection.execute(
            "INSERT INTO prompt_tests (provider, model, temperature, max_tokens, top_p, story_id, question_id, payload) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (provider, model, temperature, max_tokens, top_p, story_id, question_id, payload)
        )
        return cursor.lastrowid

def add_response(connection, prompt_test_id, response_content, full_response):
    with connection:
        connection.execute("INSERT INTO responses (prompt_test_id, response_content, full_response) VALUES (?, ?, ?)", (prompt_test_id, response_content, full_response))

def get_all_stories(connection):
    with connection:
        return connection.execute("SELECT * FROM stories").fetchall()

def get_all_questions(connection):
    with connection:
        return connection.execute("SELECT * FROM questions").fetchall()

def get_all_story_templates(connection):
    with connection:
        return connection.execute("SELECT * FROM story_templates").fetchall()

def get_all_nouns(connection):
    with connection:
        return connection.execute("SELECT * FROM nouns").fetchall()

def get_all_adjectives(connection):
    with connection:
        return connection.execute("SELECT * FROM adjectives").fetchall()

def get_story_by_id(connection, story_id):
    with connection:
        return connection.execute("SELECT * FROM stories WHERE id = ?", (story_id,)).fetchone()

def get_question_by_id(connection, question_id):
    with connection:
        return connection.execute("SELECT * FROM questions WHERE id = ?", (question_id,)).fetchone()

# Main execution
if __name__ == "__main__":
    db_file = "database.db"
    connection = sqlite3.connect(db_file)
    create_tables(connection)
    insert_initial_data(connection)