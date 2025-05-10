import pytest
from app.services import prompt_service
from app.models import Prompt, Provider, Model, Question, Story, Response

@pytest.fixture(autouse=True)
def push_app_context(app):
    ctx = app.app_context()
    ctx.push()
    yield
    ctx.pop()

class TestPromptService:
    """Test suite for the prompt_service module."""

    def test_get_filter_options(self, session, test_data):
        """Test that get_filter_options returns all providers, models, and questions."""
        options = prompt_service.get_filter_options()
        assert "providers" in options
        assert "models" in options
        assert "questions" in options
        # Check that at least the test data is present
        assert len(options["providers"]) >= len(test_data["ids"]["providers"])
        assert len(options["models"]) >= len(test_data["ids"]["models"])
        assert len(options["questions"]) >= len(test_data["ids"]["questions"])

    def test_get_filtered_prompts_no_filters(self, session, test_data):
        """Test get_filtered_prompts returns all prompts with no filters."""
        pagination = prompt_service.get_filtered_prompts()
        assert hasattr(pagination, "items")
        assert hasattr(pagination, "total")
        assert pagination.total >= len(test_data["ids"]["prompts"])
        # Each item should be a tuple (Prompt, last_used)
        for item in pagination.items:
            assert isinstance(item[0], Prompt)

    def test_get_filtered_prompts_with_provider(self, session, test_data):
        """Test filtering prompts by provider name."""
        provider = session.get(Provider, test_data["ids"]["providers"][0])
        pagination = prompt_service.get_filtered_prompts(provider=provider.provider_name)
        for item in pagination.items:
            prompt = item[0]
            model = session.get(Model, prompt.model_id)
            prov = session.get(Provider, model.provider_id)
            assert provider.provider_name.lower() in prov.provider_name.lower()

    def test_get_filtered_prompts_with_model(self, session, test_data):
        """Test filtering prompts by model name."""
        model = session.get(Model, test_data["ids"]["models"][0])
        pagination = prompt_service.get_filtered_prompts(model=model.name)
        for item in pagination.items:
            prompt = item[0]
            db_model = session.get(Model, prompt.model_id)
            assert model.name.lower() in db_model.name.lower()

    def test_get_filtered_prompts_with_question(self, session, test_data):
        """Test filtering prompts by question_id."""
        question_id = test_data["ids"]["questions"][0]
        pagination = prompt_service.get_filtered_prompts(question_id=question_id)
        for item in pagination.items:
            prompt = item[0]
            assert prompt.question_id == question_id

    def test_get_filtered_prompts_with_story(self, session, test_data):
        """Test filtering prompts by story_id."""
        story_id = test_data["ids"]["stories"][0]
        pagination = prompt_service.get_filtered_prompts(story_id=story_id)
        for item in pagination.items:
            prompt = item[0]
            assert prompt.story_id == story_id

    def test_get_filtered_prompts_with_date_range(self, session, test_data):
        """Test filtering prompts by response timestamp range."""
        # Use the timestamp from test_data responses
        from datetime import datetime, timedelta
        response_id = test_data["ids"]["responses"][0]
        response = session.get(Response, response_id)
        date_str = response.timestamp.strftime('%Y-%m-%d')
        pagination = prompt_service.get_filtered_prompts(start_date=date_str, end_date=date_str)
        # All returned prompts should have a response in the date range
        for item in pagination.items:
            prompt, last_used = item
            assert last_used is not None
            assert last_used.date() == response.timestamp.date()

    def test_get_filtered_prompts_sorting(self, session, test_data):
        """Test sorting order of prompts by last_used timestamp."""
        paged_asc = prompt_service.get_filtered_prompts(sort='date_asc')
        paged_desc = prompt_service.get_filtered_prompts(sort='date_desc')
        asc_times = [item[1] for item in paged_asc.items if item[1] is not None]
        desc_times = [item[1] for item in paged_desc.items if item[1] is not None]
        assert asc_times == sorted(asc_times)
        assert desc_times == sorted(desc_times, reverse=True)

    def test_apply_filters_helper(self, session, test_data):
        """Directly test the _apply_filters helper (optional, for coverage)."""
        stmt = prompt_service.select(Prompt)
        filtered = prompt_service._apply_filters(stmt, provider="Test Provider", model=None, question_id=None, story_id=None, start_date=None, end_date=None)
        # Should return a SQLAlchemy Select object
        from sqlalchemy.sql import Select
        assert isinstance(filtered, Select)

    def test_parse_date_helper(self):
        """Test the _parse_date helper function."""
        from app.services.prompt_service import _parse_date
        assert _parse_date("2024-01-01").year == 2024
        assert _parse_date("not-a-date") is None
        assert _parse_date(None) is None

    def test_update_prompt_selection_clear_all(self):
        """Test update_prompt_selection with clear_all action."""
        result = prompt_service.update_prompt_selection(['1', '2'], 'clear_all', {})
        assert result == []

    def test_update_prompt_selection_select_multiple(self):
        """Test update_prompt_selection with select_multiple action."""
        result = prompt_service.update_prompt_selection(['1'], 'select_multiple', {'prompt_ids': ['2', '3']})
        assert set(result) == {'1', '2', '3'}

    def test_update_prompt_selection_invert_selection(self):
        """Test update_prompt_selection with invert_selection action."""
        result = prompt_service.update_prompt_selection(['1'], 'invert_selection', {'select_ids': ['2'], 'deselect_ids': ['1']})
        assert set(result) == {'2'}

    def test_update_prompt_selection_toggle(self):
        """Test update_prompt_selection with toggle action."""
        # Add
        result = prompt_service.update_prompt_selection(['1'], 'toggle', {'prompt_id': '2', 'selected': True})
        assert set(result) == {'1', '2'}
        # Remove
        result = prompt_service.update_prompt_selection(['1', '2'], 'toggle', {'prompt_id': '2', 'selected': False})
        assert set(result) == {'1'}

    def test_get_prompts_by_ids_returns_prompts(self, session, test_data):
        """Test get_prompts_by_ids returns the correct Prompt objects."""
        prompt_ids = test_data["ids"]["prompts"]
        prompts = prompt_service.get_prompts_by_ids(prompt_ids)
        assert len(prompts) == len(prompt_ids)
        for prompt in prompts:
            assert prompt.prompt_id in prompt_ids

    def test_get_prompts_by_ids_empty(self):
        """Test get_prompts_by_ids returns empty list when given empty input."""
        prompts = prompt_service.get_prompts_by_ids([])
        assert prompts == []