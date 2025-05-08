import pytest
from app.models.prompt_response import Prompt, Response
from sqlalchemy.exc import IntegrityError

@pytest.fixture(autouse=True)
def push_app_context(app):
    ctx = app.app_context()
    ctx.push()
    yield
    ctx.pop()

class TestPromptResponseModel:
    def test_prompt_creation(self, session, test_data):
        prompt_id = test_data["ids"]["prompts"][0]
        prompt = session.get(Prompt, prompt_id)
        assert prompt is not None
        assert prompt.payload == "Test payload content"

    def test_response_creation(self, session, test_data):
        response_id = test_data["ids"]["responses"][0]
        response = session.get(Response, response_id)
        assert response is not None
        assert response.response_content == "This story is about animals and their actions."
        # Check relationship
        prompt = session.get(Prompt, response.prompt_id)
        assert response.prompt == prompt

    def test_response_without_prompt(self, session):
        # Try to create a response with a non-existent prompt_id
        response = Response(
            prompt_id=999999,  # Non-existent prompt
            response_content="Orphan response"
        )
        session.add(response)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

    def test_response_without_content(self, session, test_data):
        prompt_id = test_data["ids"]["prompts"][0]
        response = Response(
            prompt_id=prompt_id,
            response_content=None
        )
        session.add(response)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

    def test_prompt_repr(self, session, test_data):
        prompt_id = test_data["ids"]["prompts"][0]
        prompt = session.get(Prompt, prompt_id)
        assert f"<Prompt {prompt.prompt_id}>" == repr(prompt)

    def test_response_repr(self, session, test_data):
        response_id = test_data["ids"]["responses"][0]
        response = session.get(Response, response_id)
        assert f"<Response {response.response_id}>" == repr(response)