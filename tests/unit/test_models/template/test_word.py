import pytest
from app.models.template.word import Word
from app.models.template.field import Field
from sqlalchemy.exc import IntegrityError

@pytest.fixture(autouse=True)
def push_app_context(app):
    ctx = app.app_context()
    ctx.push()
    yield
    ctx.pop()

class TestWordModel:
    def test_word_creation(self, session):
        word = Word(word="unique_word")
        session.add(word)
        session.commit()
        saved = session.query(Word).filter_by(word_id=word.word_id).first()
        assert saved is not None
        assert saved.word == "unique_word"

    def test_word_unique_constraint(self, session):
        word1 = Word(word="duplicate")
        session.add(word1)
        session.commit()  # Commit the first word

        word2 = Word(word="duplicate")
        session.add(word2)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

    def test_word_without_value(self, session):
        word = Word(word=None)
        session.add(word)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

    def test_word_repr(self, session):
        word = Word(word="repr_word")
        session.add(word)
        session.commit()
        saved = session.query(Word).filter_by(word_id=word.word_id).first()
        repr_str = repr(saved)
        assert str(saved.word_id) in repr_str
        assert "repr_word" in repr_str

    def test_word_field_relationship(self, session, test_data):
        # Use test_data fixture to get existing field and word IDs
        field_id = test_data["ids"]["fields"]["animal"]
        word_id = test_data["ids"]["words"]["cat"]
        field = session.get(Field, field_id)
        word = session.get(Word, word_id)

        # Relationship should be established by fixture
        assert field in word.fields
        assert word in field.words

    def test_add_word_to_field(self, session):
        field = Field(field="test_field")
        word = Word(word="test_word")
        session.add_all([field, word])
        session.commit()

        # Add relationship
        word.fields.append(field)
        session.commit()

        # Check both sides of the relationship
        assert field in word.fields
        assert word in field.words