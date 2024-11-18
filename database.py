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

CREATE_ADJECTIVES_TABLE = """
CREATE TABLE IF NOT EXISTS adjectives (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    adjective TEXT NOT NULL
);
"""

CREATE_NOUNS_TABLE = """
CREATE TABLE IF NOT EXISTS nouns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    noun TEXT NOT NULL
);
"""

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
    test_id INTEGER NOT NULL,
    response TEXT NOT NULL,
    FOREIGN KEY (test_id) REFERENCES prompt_tests (id)
);
"""

INSERT_STORY = "INSERT INTO stories (content) VALUES (?);"
INSERT_QUESTION = "INSERT INTO questions (content) VALUES (?);"
INSERT_PROMPT_TEST = """
INSERT INTO prompt_tests (provider, model, temperature, max_tokens, top_p, story_id, question_id, payload)
VALUES (?, ?, ?, ?, ?, ?, ?, ?);
"""
INSERT_RESPONSE = """
INSERT INTO responses (test_id, response)
VALUES (?, ?);
"""

GET_ALL_STORIES = "SELECT * FROM stories;"
GET_ALL_QUESTIONS = "SELECT * FROM questions;"
GET_STORY_BY_ID = "SELECT * FROM stories WHERE id = ?;"
GET_QUESTION_BY_ID = "SELECT * FROM questions WHERE id = ?;"

def connect():
    return sqlite3.connect('database.db')

def create_tables(connection):
    with connection:
        connection.execute(CREATE_STORIES_TABLE)
        connection.execute(CREATE_QUESTIONS_TABLE)
        connection.execute(CREATE_PROMPT_TESTS_TABLE)
        connection.execute(CREATE_RESPONSES_TABLE)
        connection.execute(CREATE_STORY_TEMPLATES_TABLE)
        connection.execute(CREATE_ADJECTIVES_TABLE)
        connection.execute(CREATE_NOUNS_TABLE)

def delete_database(db_file):
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
            print(f"Deleted {db_file}")
        except PermissionError as e:
            print(f"Error: {e}")
            print("Ensure that the database connection is closed and no other process is using the file.")
    else:
        print(f"{db_file} does not exist")

def add_story(connection, content):
    with connection:
        connection.execute("INSERT INTO stories (content) VALUES (?);", (content,))

def add_question(connection, content):
    with connection:
        connection.execute("INSERT INTO questions (content) VALUES (?);", (content,))

def add_prompt_test(connection, provider, model, temperature, max_tokens, top_p, story_id, question_id, payload):
    with connection:
        cursor = connection.execute(INSERT_PROMPT_TEST, (provider, model, temperature, max_tokens, top_p, story_id, question_id, payload))
        return cursor.lastrowid  # Return the ID of the newly inserted row

def add_response(connection, test_id, response):
    with connection:
        connection.execute(INSERT_RESPONSE, (test_id, response))

def add_story_template(connection, template):
    with connection:
        connection.execute("INSERT INTO story_templates (template) VALUES (?)", (template,))

def add_adjective(connection, adjective):
    with connection:
        connection.execute("INSERT INTO adjectives (adjective) VALUES (?)", (adjective,))

def add_noun(connection, noun):
    with connection:
        connection.execute("INSERT INTO nouns (noun) VALUES (?)", (noun,))

def get_all_stories(connection):
    with connection:
        return connection.execute(GET_ALL_STORIES).fetchall()

def get_all_questions(connection):
    with connection:
        return connection.execute(GET_ALL_QUESTIONS).fetchall()

def get_story_by_id(connection, story_id):
    with connection:
        return connection.execute(GET_STORY_BY_ID, (story_id,)).fetchone()

def get_question_by_id(connection, question_id):
    with connection:
        return connection.execute(GET_QUESTION_BY_ID, (question_id,)).fetchone()


if __name__ == "__main__":
    db_file = 'database.db'
    delete_database(db_file)
    connection = connect()
    create_tables(connection)
    print("Database and tables created.")
    connection.close()