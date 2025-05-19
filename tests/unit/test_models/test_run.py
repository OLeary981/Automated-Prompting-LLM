import pytest
from app.models import Run, Response, Prompt
from sqlalchemy.exc import IntegrityError

@pytest.fixture(autouse=True)
def push_app_context(app):
    ctx = app.app_context()
    ctx.push()
    yield
    ctx.pop()

class TestRunModel:

    def test_run_creation_and_response_link(self, session, test_data):
        # Arrange
        prompt_id = test_data["ids"]["prompts"][0]

        # Act: Create a Run and a linked Response
        run = Run(description="Test run entry")
        session.add(run)
        session.commit()

        response = Response(
            prompt_id=prompt_id,
            response_content="Linked to run",
            run_id=run.run_id
        )
        session.add(response)
        session.commit()

        # Assert
        fetched = session.get(Response, response.response_id)
        assert fetched.run_id == run.run_id
        assert fetched.run.description == "Test run entry"

    def test_response_run_fk_enforced(self, session, test_data):
        # Try assigning a non-existent run_id
        prompt_id = test_data["ids"]["prompts"][0]
        response = Response(
            prompt_id=prompt_id,
            response_content="Invalid run link",
            run_id=999999  # does not exist
        )
        session.add(response)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

    def test_run_deletion_blocked_if_used(self, session, test_data):
        # Arrange
        prompt_id = test_data["ids"]["prompts"][0]
        run = Run(description="Used run")
        session.add(run)
        session.commit()

        response = Response(
            prompt_id=prompt_id,
            response_content="Tied to run",
            run_id=run.run_id
        )
        session.add(response)
        session.commit()

        # Try deleting the run
        session.delete(run)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

    def test_orphan_run_deletion_allowed(self, session):
        # A run not linked to any responses should delete fine
        run = Run(description="Orphan run")
        session.add(run)
        session.commit()
        session.delete(run)
        session.commit()

        assert session.get(Run, run.run_id) is None