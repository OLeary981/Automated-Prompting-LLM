import pytest
from app.services import category_service
from app.models import Category, StoryCategory

@pytest.fixture(autouse=True)
def push_app_context(app):
    ctx = app.app_context()
    ctx.push()
    yield
    ctx.pop()

class TestCategoryService:
    """Tests for the category_service."""

    def test_get_all_categories(self, session, test_data):
        """Test retrieving all categories."""
        categories = category_service.get_all_categories()
        assert len(categories) >= len(test_data["ids"]["categories"])
        names = [c.category for c in categories]
        for cat_id in test_data["ids"]["categories"]:
            cat = session.get(Category, cat_id)
            assert cat.category in names

    def test_add_category_new(self, session):
        """Test adding a new category."""
        new_name = "Brand New Category"
        cat_id = category_service.add_category(new_name)
        cat = session.get(Category, cat_id)
        assert cat is not None
        assert cat.category == new_name

    def test_add_category_existing(self, session, test_data):
        """Test adding a category that already exists returns its id."""
        cat_id = test_data["ids"]["categories"][0]
        cat = session.get(Category, cat_id)
        returned_id = category_service.add_category(cat.category)
        assert returned_id == cat_id

    def test_get_categories_for_story(self, session, test_data):
        """Test retrieving categories for a story."""
        story_id = test_data["ids"]["stories"][0]
        categories = category_service.get_categories_for_story(story_id)
        assert isinstance(categories, list)
        # Should match the StoryCategory relationship in test_data
        sc_links = [sc for sc in test_data["ids"]["story_categories"] if sc[0] == story_id]
        expected_cat_ids = set(sc[1] for sc in sc_links)
        actual_cat_ids = set(cat.category_id for cat in categories)
        assert expected_cat_ids == actual_cat_ids

    def test_set_categories_for_story(self, session, test_data):
        """Test setting categories for a story (replacing existing associations)."""
        story_id = test_data["ids"]["stories"][0]
        # Add a new category to associate
        new_cat_id = category_service.add_category("Temporary Category")
        category_service.set_categories_for_story(story_id, [new_cat_id])
        # Only the new category should be associated now
        links = session.query(StoryCategory).filter_by(story_id=story_id).all()
        assert len(links) == 1
        assert links[0].category_id == new_cat_id