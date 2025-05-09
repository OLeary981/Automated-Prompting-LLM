import pytest
from app.services import story_service
from app.models import Story, StoryCategory, Category
from werkzeug.exceptions import NotFound

@pytest.fixture(autouse=True)
def push_app_context(app):
    ctx = app.app_context()
    ctx.push()
    yield
    ctx.pop()

class TestStoryService:
    """Test suite for the story_service module."""

    def test_add_story_without_categories(self, session):
        """Test adding a story with no categories."""
        story_content = "A story without categories"
        story_id = story_service.add_story(story_content)
        story = session.query(Story).filter_by(story_id=story_id).first()
        assert story is not None
        assert story.content == story_content
        assert session.query(StoryCategory).filter_by(story_id=story_id).count() == 0

    def test_add_story_with_categories(self, session, test_data):
        """Test adding a story with existing categories."""
        story_content = "A story with categories"
        category_ids = test_data["ids"]["categories"]
        story_id = story_service.add_story(story_content, category_ids)
        story = session.query(Story).filter_by(story_id=story_id).first()
        assert story is not None
        assert story.content == story_content
        links = session.query(StoryCategory).filter_by(story_id=story_id).all()
        assert len(links) == len(category_ids)
        assert set(sc.category_id for sc in links) == set(category_ids)

    def test_add_story_with_categories_and_new_category(self, session, mocker, test_data):
        """Test adding a story with existing and a new category."""
        # Mock category_service.add_category to return a new id
        mock_add_category = mocker.patch('app.services.category_service.add_category', return_value=999)
        # Ensure the new category exists in the DB for FK constraint
        session.add(Category(category_id=999, category="Brand New Category"))
        session.commit()

        story_content = "A story with new category"
        category_ids = test_data["ids"]["categories"][:]
        new_category = "Brand New Category"
        story_id = story_service.add_story_with_categories(story_content, category_ids, new_category)
        story = session.query(Story).filter_by(story_id=story_id).first()
        assert story is not None
        assert story.content == story_content
        mock_add_category.assert_called_once_with(new_category.strip())
        links = session.query(StoryCategory).filter_by(story_id=story_id).all()
        expected_ids = set(test_data["ids"]["categories"] + [999])
        assert set(sc.category_id for sc in links) == expected_ids




#THIS IS AN INTEGRATION TEST? BELONGS ELSEWHERE
    # def test_add_story_with_categories_and_new_category_integration(self, session, test_data):
    #     """Integration test: adding a story with existing and a new category (no mocking)."""
    #     story_content = "A story with a new category"
    #     category_ids = test_data["ids"]["categories"][:]  # e.g. [1, 2]
    #     new_category = "Brand New Category"

    #     # Call the real service (no mocking)
    #     story_id = story_service.add_story_with_categories(story_content, category_ids, new_category)

    #     # The new category should now exist in the DB
    #     new_cat = session.query(Category).filter_by(category=new_category).first()
    #     assert new_cat is not None

    #     # The story should exist
    #     story = session.query(Story).filter_by(story_id=story_id).first()
    #     assert story is not None
    #     assert story.content == story_content

    #     # The story should be linked to all original categories + the new one
    #     links = session.query(StoryCategory).filter_by(story_id=story_id).all()
    #     linked_category_ids = {sc.category_id for sc in links}
    #     expected_ids = set(test_data["ids"]["categories"] + [new_cat.category_id])
    #     assert linked_category_ids == expected_ids


    def test_get_all_stories(self, session, test_data):
        """Test retrieving all stories."""
        stories = story_service.get_all_stories()
        assert len(stories) >= len(test_data["ids"]["stories"])
        contents = [s.content for s in stories]
        for story_id in test_data["ids"]["stories"]:
            story = session.get(Story, story_id)
            assert story.content in contents

    def test_get_story_by_id(self, session, test_data):
        """Test retrieving a story by its ID."""
        story_id = test_data["ids"]["stories"][0]
        story = story_service.get_story_by_id(story_id)
        assert story is not None
        assert story.story_id == story_id

    def test_delete_story(self, session, test_data):
        """Test deleting a story by ID."""
        story_content = "Story to delete"
        story_id = story_service.add_story(story_content)
        assert session.query(Story).filter_by(story_id=story_id).first() is not None
        result = story_service.delete_story(story_id)
        assert result is True
        assert session.query(Story).filter_by(story_id=story_id).first() is None

    def test_delete_story_returns_false_if_not_found(self, session):
        """Test deleting a non-existent story returns False."""
        result = story_service.delete_story(999999)
        assert result is False

    def test_get_story_by_id_404(session):
        """Test that get_story_by_id aborts with 404 for missing story."""
        non_existent_id = 999999
        with pytest.raises(NotFound):
            story_service.get_story_by_id(non_existent_id)