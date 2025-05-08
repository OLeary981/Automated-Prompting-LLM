# import pytest
# from app.models.question import Question
# from sqlalchemy.exc import IntegrityError

# class TestQuestionModel:
#     def test_question_creation(self, app, session):
#         """Test that a question can be created with valid data."""
#         with app.app_context():
#             question = Question(content="What is the capital of France?")
#             session.add(question)
#             session.commit()

#             saved = session.query(Question).filter_by(question_id=question.question_id).first()
#             assert saved is not None
#             assert saved.content == "What is the capital of France?"

#     def test_question_without_content(self, app, session):
#         """Test that a question cannot be created without content."""
#         with app.app_context():
#             question = Question(content=None)
#             session.add(question)
#             with pytest.raises(IntegrityError):
#                 session.commit()
#             session.rollback()

#     def test_question_repr(self, app, session):
#         """Test the __repr__ method of the Question model."""
#         with app.app_context():
#             question = Question(content="Sample question?")
#             session.add(question)
#             session.commit()
#             saved = session.query(Question).filter_by(question_id=question.question_id).first()
#             repr_str = repr(saved)
#             assert str(saved.question_id) in repr_str
#             assert "Sample question?" in repr_str

import pytest
from app.models.question import Question
from sqlalchemy.exc import IntegrityError

@pytest.fixture(autouse=True)
def push_app_context(app):
    ctx = app.app_context()
    ctx.push()
    yield
    ctx.pop()

class TestQuestionModel:
    def test_question_creation(self, session):
        question = Question(content="What is the capital of France?")
        session.add(question)
        session.commit()
        saved = session.query(Question).filter_by(question_id=question.question_id).first()
        assert saved is not None
        assert saved.content == "What is the capital of France?"

    def test_question_without_content(self, session):
        question = Question(content=None)
        session.add(question)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

    def test_question_repr(self, session):
        question = Question(content="Sample question?")
        session.add(question)
        session.commit()
        saved = session.query(Question).filter_by(question_id=question.question_id).first()
        repr_str = repr(saved)
        assert str(saved.question_id) in repr_str
        assert "Sample question?" in repr_str