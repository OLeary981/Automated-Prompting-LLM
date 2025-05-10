import pytest
from app.models.template.template import Template
from sqlalchemy.exc import IntegrityError

@pytest.fixture(autouse=True)
def push_app_context(app):
    ctx = app.app_context()
    ctx.push()
    yield
    ctx.pop()

class TestTemplateModel:
    def test_template_creation(self, session):
        template = Template(content="A test template content")
        session.add(template)
        session.commit()
        saved = session.query(Template).filter_by(template_id=template.template_id).first()
        assert saved is not None
        assert saved.content == "A test template content"

    def test_template_without_content(self, session):
        template = Template(content=None)
        session.add(template)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

    def test_template_repr(self, session, test_data):
        template_id = test_data["ids"]["templates"][0]
        template = session.get(Template, template_id)
        repr_str = repr(template)
        assert str(template.template_id) in repr_str
        assert str(template.content) in repr_str