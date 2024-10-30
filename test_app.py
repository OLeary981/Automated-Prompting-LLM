import unittest
import sqlite3
import database
from app import call_LLM_GROQ, prompt_create_and_send_db_prompt

class TestDatabaseFunctions(unittest.TestCase):

    def setUp(self):
        # Create an in-memory database for testing
        self.connection = sqlite3.connect(":memory:")
        database.create_tables(self.connection)

    def tearDown(self):
        self.connection.close()

    def test_add_story(self):
        database.add_story(self.connection, "Test story content")
        story = database.get_story_by_id(self.connection, 1)
        self.assertIsNotNone(story)
        self.assertEqual(story[1], "Test story content")

    def test_add_question(self):
        database.add_question(self.connection, "Test question content")
        question = database.get_question_by_id(self.connection, 1)
        self.assertIsNotNone(question)
        self.assertEqual(question[1], "Test question content")

    def test_add_prompt_test(self):
        database.add_story(self.connection, "Test story content")
        story_id = self.connection.execute("SELECT last_insert_rowid();").fetchone()[0]
        database.add_question(self.connection, "Test question content")
        question_id = self.connection.execute("SELECT last_insert_rowid();").fetchone()[0]
        prompt_test_id = database.add_prompt_test(self.connection, story_id, question_id)
        self.assertIsNotNone(prompt_test_id)

    def test_add_response(self):
        database.add_story(self.connection, "Test story content")
        story_id = self.connection.execute("SELECT last_insert_rowid();").fetchone()[0]
        database.add_question(self.connection, "Test question content")
        question_id = self.connection.execute("SELECT last_insert_rowid();").fetchone()[0]
        prompt_test_id = database.add_prompt_test(self.connection, story_id, question_id)
        database.add_response(self.connection, prompt_test_id, "Test response content")
        response = self.connection.execute("SELECT * FROM responses WHERE test_id = ?", (prompt_test_id,)).fetchone()
        self.assertIsNotNone(response)
        self.assertEqual(response[2], "Test response content")

class TestAppFunctions(unittest.TestCase):

    def setUp(self):
        # Create an in-memory database for testing
        self.connection = sqlite3.connect(":memory:")
        database.create_tables(self.connection)

    def tearDown(self):
        self.connection.close()

    def test_call_LLM_GROQ(self):
        # Mock the LLM response
        story = "Test story content"
        question = "Test question content"
        response = call_LLM_GROQ(story, question)
        self.assertIsInstance(response, str)

    def test_prompt_create_and_send_db_prompt(self):
        # Add test data
        database.add_story(self.connection, "Test story content")
        database.add_question(self.connection, "Test question content")

        # Mock user input
        def mock_input(prompt):
            if "story" in prompt:
                return "1"
            elif "question" in prompt:
                return "1"
            return ""

        # Replace input function with mock_input
        original_input = __builtins__.input
        __builtins__.input = mock_input

        try:
            prompt_create_and_send_db_prompt(self.connection)
            response = self.connection.execute("SELECT * FROM responses").fetchone()
            self.assertIsNotNone(response)
        finally:
            # Restore original input function
            __builtins__.input = original_input

if __name__ == "__main__":
    unittest.main()