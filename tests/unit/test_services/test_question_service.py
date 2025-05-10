import pytest
from app.services import question_service
from app.models import Question

@pytest.fixture(autouse=True)
def push_app_context(app):
    ctx = app.app_context()
    ctx.push()
    yield
    ctx.pop()

class TestQuestionService:

    def test_get_all_questions(self, session, test_data):
        """Test get_all_questions returns all questions from test_data."""
        questions = question_service.get_all_questions()
        ids = [q.question_id for q in questions]
        for qid in test_data["ids"]["questions"]:
            assert qid in ids

    def test_add_question(self, session):
        """Test add_question adds a new question and returns its ID."""
        content = "What is your favorite color?"
        qid = question_service.add_question(content)
        question = session.get(Question, qid)
        assert question is not None
        assert question.content == content

    def test_get_question_by_id_existing(self, session, test_data):
        """Test get_question_by_id returns the correct question from test_data."""
        qid = test_data["ids"]["questions"][0]
        question = question_service.get_question_by_id(qid)
        assert question is not None
        assert question.question_id == qid

    def test_get_question_by_id_nonexistent(self, session):
        """Test get_question_by_id returns None for a non-existent question."""
        # 999999 is assumed not to exist in test DB
        question = question_service.get_question_by_id(999999)
        assert question is None