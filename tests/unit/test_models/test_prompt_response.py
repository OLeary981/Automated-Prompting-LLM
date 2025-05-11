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
    def test_prompt_fixture_retrieval(self, session, test_data):
        prompt_id = test_data["ids"]["prompts"][0]
        prompt = session.get(Prompt, prompt_id)
        assert prompt is not None
        assert prompt.payload == "Test payload content"
    
    def test_prompt_true_creation(self, session, test_data):
    # Arrange: get a valid model_id, story_id, question_id from fixture
        model_id = test_data["ids"]["models"][0]
        story_id = test_data["ids"]["stories"][0]
        question_id = test_data["ids"]["questions"][0]
        # Act: create and add a new Prompt
        prompt = Prompt(
            model_id=model_id,
            story_id=story_id,
            question_id=question_id,
            temperature=0.5,
            max_tokens=50,
            top_p=0.9,
            payload="unit_test_created_prompt"
        )
        session.add(prompt)
        session.commit()
        # Assert: fetch from DB and check fields
        fetched = session.get(Prompt, prompt.prompt_id)
        assert fetched is not None
        assert fetched.payload == "unit_test_created_prompt"
        assert fetched.model_id == model_id
    
    def test_response_fixture_retrieval(self, session, test_data):
        response_id = test_data["ids"]["responses"][0]
        response = session.get(Response, response_id)
        assert response is not None
        assert response.response_content == "conf_test_response_content"

    def test_response_true_creation(self, session, test_data):
        # Arrange: get a valid prompt_id from the fixture
        prompt_id = test_data["ids"]["prompts"][0]
        # Act: create and add a new Response
        response = Response(
            prompt_id=prompt_id,
            response_content="unit_test_created_response"
        )
        session.add(response)
        session.commit()
        # Assert: fetch from DB and check fields
        fetched = session.get(Response, response.response_id)
        assert fetched is not None
        assert fetched.response_content == "unit_test_created_response"
        assert fetched.prompt_id == prompt_id
        # Optionally check relationship
        assert fetched.prompt == session.get(Prompt, prompt_id)

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