import datetime

import pytest

from app.models import Model, Provider, Question, Response, Story, Template
from app.services import response_service


@pytest.fixture(autouse=True)
def push_app_context(app):
    ctx = app.app_context()
    ctx.push()
    yield
    ctx.pop()

class TestResponseService:
    """Test suite for the response_service module."""

    def test_get_dynamic_filter_options(self, session, test_data):
        """Test that get_filter_options returns all providers, models, and questions."""
        options = response_service.get_dynamic_filter_options()
        assert "providers" in options
        assert "models" in options
        assert "questions" in options
        assert len(options["providers"]) >= len(test_data["ids"]["providers"])
        assert len(options["models"]) >= len(test_data["ids"]["models"])
        assert len(options["questions"]) >= len(test_data["ids"]["questions"])

    def test_get_responses_paginated(self, session, test_data):
        """Test paginated response retrieval."""
        pagination = response_service.get_responses_paginated(page=1, per_page=2)
        assert hasattr(pagination, "items")
        assert hasattr(pagination, "total")
        assert isinstance(pagination.items, list)
        assert pagination.page == 1
        assert pagination.per_page == 2

    def test_get_source_info_prompt(self, session, test_data):
        """Test get_source_info for a prompt."""
        prompt_id = test_data["ids"]["prompts"][0]
        info = response_service.get_source_info("prompt", source_id=prompt_id)
        assert f"Prompt #{prompt_id}" in info

    def test_get_source_info_story(self, session, test_data):
        """Test get_source_info for a story."""
        story_id = test_data["ids"]["stories"][0]
        info = response_service.get_source_info("story", source_id=story_id)
        assert f"Story #{story_id}" in info

    #extra test to fix gap in coverage for multiple storeis
    def test_get_source_info_story_multiple(self):
        result = response_service.get_source_info("story", source_count=2)
        assert result == "2 Selected Stories"

    def test_get_source_info_template(self, session, test_data):
        """Test get_source_info for a template."""
        template_id = test_data["ids"]["templates"][0]
        info = response_service.get_source_info("template", source_id=template_id)
        assert f"Template #{template_id}" in info

    #extra test to fix gap in coverage for multiple templates
    def test_get_source_info_template_multiple(self):
        result = response_service.get_source_info("template", source_count=2)
        assert result == "2 Selected Templates"

    def test_update_response_flag(self, session, test_data):
        """Test updating the flagged status of a response."""
        response_id = test_data["ids"]["responses"][0]
        ok, err = response_service.update_response_flag(response_id, True)
        assert ok is True
        updated = session.get(Response, response_id)
        assert updated.flagged_for_review is True

    def test_update_response_review(self, session, test_data):
        """Test updating the flagged status and review notes of a response."""
        response_id = test_data["ids"]["responses"][0]
        ok, err = response_service.update_response_review(response_id, True, "Test review")
        assert ok is True
        updated = session.get(Response, response_id)
        assert updated.flagged_for_review is True
        assert updated.review_notes == "Test review"

    def test_get_responses_for_prompt(self, session, test_data):
        """Test getting responses for a specific prompt."""
        prompt_id = test_data["ids"]["prompts"][0]
        responses = response_service.get_responses_for_prompt(prompt_id)
        assert isinstance(responses, list)
        for resp in responses:
            assert resp.prompt_id == prompt_id

    def test_get_responses_for_stories(self, session, test_data):
        """Test getting responses for a list of stories."""
        story_ids = test_data["ids"]["stories"][:2]
        responses = response_service.get_responses_for_stories(story_ids)
        assert isinstance(responses, list)
        for resp in responses:
            assert resp.prompt.story_id in story_ids

    def test_get_responses_for_templates(self, session, test_data):
        """Test getting responses for a list of templates."""
        print("TEMPLATE IDS:", test_data["ids"]["templates"])#investigateing if this is empty to see if that explains gap in coverage.
        template_ids = test_data["ids"]["templates"][:2]
        responses = response_service.get_responses_for_templates(template_ids)
        assert isinstance(responses, list)
        for resp in responses:
            assert resp.prompt.story.template_id in template_ids
    
    #test to cover for template ids as strigns
    def test_get_responses_for_templates_with_string_ids(self, session, test_data):
        template_ids = [str(tid) for tid in test_data["ids"]["templates"][:2]]
        responses = response_service.get_responses_for_templates(template_ids)
        assert isinstance(responses, list)
        for resp in responses:
            assert str(resp.prompt.story.template_id) in template_ids

    def test_generate_csv_export(self, session, test_data):
        """Test CSV export generation for responses."""
        response_id = test_data["ids"]["responses"][0]
        responses = [session.get(Response, response_id)]
        csv_data = response_service.generate_csv_export(responses)
        assert "ID,Date,Time,Provider,Model" in csv_data
        assert str(response_id) in csv_data

#more tests for edge cases and to cover type conversion lines
    def test_to_int_list_with_strings(self):
        result = response_service._to_int_list(['1', '2', 3])
        assert result == [1, 2, 3]

    def test_get_responses_for_stories_with_string_ids(self, session, test_data):
        """Test getting responses for a list of stories with string IDs (covers int conversion)."""
        story_ids = [str(sid) for sid in test_data["ids"]["stories"][:2]]
        responses = response_service.get_responses_for_stories(story_ids)
        assert isinstance(responses, list)
        for resp in responses:
            assert str(resp.prompt.story_id) in story_ids

    def test_build_response_query_filters(self, session, test_data):
        # Test response_ids filter
        response_ids = test_data["ids"]["responses"][:2]
        stmt = response_service.build_response_query(response_ids=response_ids)
        results = session.execute(stmt).scalars().all()
        for resp in results:
            assert resp.response_id in response_ids

        # Test story_ids filter
        story_ids = test_data["ids"]["stories"][:2]
        stmt = response_service.build_response_query(story_ids=story_ids)
        results = session.execute(stmt).scalars().all()
        for resp in results:
            assert resp.prompt.story_id in story_ids

        # Test template_ids filter
        template_ids = test_data["ids"]["templates"][:2]
        stmt = response_service.build_response_query(template_ids=template_ids)
        results = session.execute(stmt).scalars().all()
        for resp in results:
            assert resp.prompt.story.template_id in template_ids

        # Test provider filter
        provider_name = session.get(Provider, test_data["ids"]["providers"][0]).provider_name
        stmt = response_service.build_response_query(provider=provider_name)
        results = session.execute(stmt).scalars().all()
        for resp in results:
            assert resp.prompt.model.provider.provider_name == provider_name

        # Test model filter
        model_name = session.get(Model, test_data["ids"]["models"][0]).name
        stmt = response_service.build_response_query(model=model_name)
        results = session.execute(stmt).scalars().all()
        for resp in results:
            assert resp.prompt.model.name == model_name

        # Test flagged_only filter
        stmt = response_service.build_response_query(flagged_only=True)
        results = session.execute(stmt).scalars().all()
        for resp in results:
            assert resp.flagged_for_review is True

        # Test question_id filter
        qid = test_data["ids"]["questions"][0]
        stmt = response_service.build_response_query(question_id=qid)
        results = session.execute(stmt).scalars().all()
        for resp in results:
            assert resp.prompt.question_id == qid

        # Test story_id filter
        sid = test_data["ids"]["stories"][0]
        stmt = response_service.build_response_query(story_id=sid)
        results = session.execute(stmt).scalars().all()
        for resp in results:
            assert resp.prompt.story_id == sid

        # Test start_date and end_date filters
        stmt = response_service.build_response_query(start_date="2020-01-01", end_date="2025-01-01")
        results = session.execute(stmt).scalars().all()
        for resp in results:
            assert resp.timestamp >= datetime.datetime(2020, 1, 1)
            assert resp.timestamp < datetime.datetime(2025, 1, 2)

        # Test sort order (date_asc)
        stmt = response_service.build_response_query(sort="date_asc")
        results = session.execute(stmt).scalars().all()
        timestamps = [resp.timestamp for resp in results]
        assert timestamps == sorted(timestamps)

    def test_build_response_query_invalid_start_date(self, session, test_data):
        """Test that an invalid start_date string triggers the ValueError branch."""
        query = response_service.build_response_query(start_date="not-a-date")
        # Just ensure it doesn't raise and returns a query object
        assert query is not None

    def test_build_response_query_invalid_end_date(self, session, test_data):
        """Test that an invalid end_date string triggers the ValueError branch."""
        query = response_service.build_response_query(end_date="not-a-date")
        # Just ensure it doesn't raise and returns a query object
        assert query is not None

    def test_get_source_info_none(self):
        assert response_service.get_source_info(None) is None

    def test_get_source_info_not_found(self):
        # Use a non-existent ID
        assert response_service.get_source_info("prompt", source_id=999999) is None
        assert response_service.get_source_info("story", source_id=999999) is None
        assert response_service.get_source_info("template", source_id=999999) is None

    def test_update_response_flag_not_found(self):
        ok, err = response_service.update_response_flag(999999, True)
        assert ok is False
        assert "not found" in err.lower()

    def test_update_response_review_not_found(self):
        ok, err = response_service.update_response_review(999999, True, "notes")
        assert ok is False
        assert "not found" in err.lower()

    def test_update_response_review_exception(self, session, test_data, monkeypatch):
        response_id = test_data["ids"]["responses"][0]
        monkeypatch.setattr(session, "commit", lambda: (_ for _ in ()).throw(Exception("fail")))
        ok, err = response_service.update_response_review(response_id, True, "notes")
        assert ok is False
        assert "fail" in err

    def test_update_response_flag_exception(self, session, test_data, monkeypatch):
        response_id = test_data["ids"]["responses"][0]
        monkeypatch.setattr(session, "commit", lambda: (_ for _ in ()).throw(Exception("fail")))
        ok, err = response_service.update_response_flag(response_id, True)
        assert ok is False
        assert "fail" in err

    def test_generate_csv_export_empty(self):
        csv_data = response_service.generate_csv_export([])
        assert "ID,Date,Time,Provider,Model" in csv_data