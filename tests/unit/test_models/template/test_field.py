import pytest
from app.models.template.field import Field
from app.models.template.word import Word
from sqlalchemy.exc import IntegrityError

@pytest.fixture(autouse=True)
def push_app_context(app):
    ctx = app.app_context()
    ctx.push()
    yield
    ctx.pop()

class TestFieldModel:
    def test_field_creation(self, session):
        field = Field(field="unique_field")
        session.add(field)
        session.commit()
        saved = session.query(Field).filter_by(field_id=field.field_id).first()
        assert saved is not None
        assert saved.field == "unique_field"

    def test_field_unique_constraint(self, session):
        field1 = Field(field="duplicate_field")
        session.add(field1)
        session.commit()  # Commit the first field

        field2 = Field(field="duplicate_field")
        session.add(field2)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

    def test_field_repr(self, session):
        field = Field(field="repr_field")
        session.add(field)
        session.commit()
        saved = session.query(Field).filter_by(field_id=field.field_id).first()
        repr_str = repr(saved)
        assert str(saved.field_id) in repr_str
        assert "repr_field" in repr_str