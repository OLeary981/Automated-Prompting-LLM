import pytest
from app.models.story import Story, Category, StoryCategory
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text


class TestStoryModel:
    """Test suite for the Story model."""

    def test_story_creation(self, app, session):
        """Test that a story can be created with valid data."""
        with app.app_context():
            # Create a basic template for the story
            from app.models import Template
            template = Template(content="Test template content")
            session.add(template)
            session.commit()

            # Create a story
            story = Story(content="Test story content", template_id=template.template_id)
            session.add(story)
            session.commit()

            # Retrieve the story
            saved_story = session.query(Story).filter_by(story_id=story.story_id).first()

            # Test basic properties
            assert saved_story is not None
            assert saved_story.content == "Test story content"
            assert saved_story.template_id == template.template_id
            assert saved_story.template == template

    def test_template_story_link_from_fixture(self, app, session, test_data):
        """Test that template.stories returns all stories with that template_id."""
        with app.app_context():
            from app.models import Template, Story
            template_id = test_data["ids"]["templates"][0]
            template = session.get(Template, template_id)
            # Get all stories with this template_id
            expected_stories = session.query(Story).filter_by(template_id=template_id).all()
            # The stories related to the template via the relationship
            related_stories = template.stories

            # Both lists should have the same story_ids
            expected_ids = {s.story_id for s in expected_stories}
            related_ids = {s.story_id for s in related_stories}
            assert expected_ids == related_ids

    def test_story_without_content(self, app, session):
        """Test that a story cannot be created without content."""
        with app.app_context():
            # Get a template ID from the test data
            from app.models import Template
            template = Template(content="Test template")
            session.add(template)
            session.commit()

            # Try to create a story without content
            story = Story(content=None, template_id=template.template_id)
            session.add(story)
            
            # Should raise an integrity error due to nullable=False
            with pytest.raises(IntegrityError):
                session.commit()
            
            # Roll back the session after the error
            session.rollback()

    def test_story_without_template(self, app, session):
        """Test that a story can be created without a template."""
        with app.app_context():
            # Create a story without a template ID
            story = Story(content="Test content without template")
            session.add(story)
            
            # Should NOT raise an error if template is optional
            session.commit()
            
            # Retrieve the story and check properties
            saved_story = session.query(Story).filter_by(story_id=story.story_id).first()
            assert saved_story is not None
            assert saved_story.template_id is None
    
    def test_story_without_template_and_category(self, app, session):
        """Test that a story can be created without a template or category."""
        with app.app_context():
            # Create a simple story without template or category
            story = Story(content="Independent story with no template or category")
            session.add(story)
            session.commit()
            
            # Retrieve the story
            saved_story = session.query(Story).filter_by(story_id=story.story_id).first()
            
            # Test basic properties
            assert saved_story is not None
            assert saved_story.content == "Independent story with no template or category"
            assert saved_story.template_id is None
            
            # Verify it has no template relationship
            assert saved_story.template is None
            
            # Verify it has no categories
            assert len(saved_story.story_categories) == 0

    def test_mixed_stories_with_and_without_templates(self, app, session):
        """Test that stories with and without templates can coexist."""
        with app.app_context():
            # Create a template
            from app.models import Template
            template = Template(content="Test template content")
            session.add(template)
            session.commit()
            
            # Create stories with and without templates
            story_with_template = Story(
                content="Story with template", 
                template_id=template.template_id
            )
            story_without_template = Story(
                content="Story without template"
            )
            
            session.add_all([story_with_template, story_without_template])
            session.commit()
            
            # Check both stories exist
            all_stories = session.query(Story).all()
            assert len(all_stories) == 2
            
            # Check template relationships
            stories_with_template = [s for s in all_stories if s.template_id is not None]
            stories_without_template = [s for s in all_stories if s.template_id is None]
            
            assert len(stories_with_template) == 1
            assert len(stories_without_template) == 1
            
            # Verify relationship navigation
            assert stories_with_template[0].template == template
            assert stories_without_template[0].template is None

    def test_story_representation(self, app, session, test_data):
        """Test the __repr__ method of the Story model."""
        with app.app_context():
            story_id = test_data["ids"]["stories"][0]
            story = session.get(Story, story_id)
            repr_string = repr(story)
            assert str(story.story_id) in repr_string
            assert str(story.content) in repr_string


class TestCategoryModel:
    """Test suite for the Category model."""

    def test_category_creation(self, app, session):
        """Test that a category can be created with valid data."""
        with app.app_context():
            category = Category(category="Test Category")
            session.add(category)
            session.commit()

            saved_category = session.query(Category).filter_by(category_id=category.category_id).first()

            assert saved_category is not None
            assert saved_category.category == "Test Category"

    def test_category_without_name(self, app, session):
        """Test that a category cannot be created without a name."""
        with app.app_context():
            category = Category(category=None)
            session.add(category)
            
            with pytest.raises(IntegrityError):
                session.commit()
            
            session.rollback()

    def test_category_representation(self, app, session):
        """Test the __repr__ method of the Category model."""
        with app.app_context():
            category = Category(category="Test Category")
            session.add(category)
            session.commit()
            
            repr_string = repr(category)
            assert str(category.category_id) in repr_string
            assert "Test Category" in repr_string


class TestStoryCategoryRelationship:
    """Test suite for the StoryCategory relationship."""

    def test_story_category_creation(self, app, session):
        """Test that a story-category relationship can be created."""
        with app.app_context():
            # Create a template
            from app.models import Template
            template = Template(content="Test template")
            session.add(template)
            session.commit()
            
            # Create a story and category
            story = Story(content="Story with category", template_id=template.template_id)
            category = Category(category="Fiction")
            
            session.add_all([story, category])
            session.commit()
            
            # Create the relationship
            story_category = StoryCategory(story_id=story.story_id, category_id=category.category_id)
            session.add(story_category)
            session.commit()
            
            # Test the relationship
            assert story_category in story.story_categories
            assert story_category in category.story_categories
            assert story_category.story == story
            assert story_category.category == category

    def test_story_category_without_story(self, app, session):
        """Test that a story-category relationship cannot be created without a story."""
        with app.app_context():
            # First check if foreign key constraints are enabled
            result = session.execute(text("PRAGMA foreign_keys")).scalar()
            assert result == 1, "Foreign key constraints are not enabled"
            
            # Create a category
            category = Category(category="Non-fiction")
            session.add(category)
            session.commit()
            
            # Try to create relationship without a valid story (story_id= 999 does not exist)
            story_category = StoryCategory(story_id=999, category_id=category.category_id)
            session.add(story_category)
            
            # This should now fail with IntegrityError
            with pytest.raises(IntegrityError):
                session.commit()
            
            session.rollback()

    def test_story_category_without_category(self, app, session):
        """Test that a story-category relationship cannot be created without a category."""
        with app.app_context():
            # Create a template and story
            from app.models import Template
            template = Template(content="Test template")
            session.add(template)
            session.commit()
            
            story = Story(content="Story without category", template_id=template.template_id)
            session.add(story)
            session.commit()
            
            # Try to create relationship without a valid category
            story_category = StoryCategory(story_id=story.story_id, category_id=999)
            session.add(story_category)
            
            with pytest.raises(IntegrityError):
                session.commit()
            
            session.rollback()

    def test_story_category_relationship_navigation(self, app, session):
        """Test navigation through the story-category relationship."""
        with app.app_context():
            # Create template, story and categories
            from app.models import Template
            template = Template(content="Test template")
            session.add(template)
            session.commit()
            
            story = Story(content="Story with multiple categories", template_id=template.template_id)
            category1 = Category(category="Fantasy")
            category2 = Category(category="Adventure")
            
            session.add_all([story, category1, category2])
            session.commit()
            
            # Create relationships
            sc1 = StoryCategory(story_id=story.story_id, category_id=category1.category_id)
            sc2 = StoryCategory(story_id=story.story_id, category_id=category2.category_id)
            
            session.add_all([sc1, sc2])
            session.commit()
            
            # Test navigation
            assert len(story.story_categories) == 2
            assert sc1 in story.story_categories
            assert sc2 in story.story_categories
            
            # Test easy category access through relationships
            categories = [sc.category for sc in story.story_categories]
            assert category1 in categories
            assert category2 in categories
            
            # Test easy story access through relationships
            stories = [sc.story for sc in category1.story_categories]
            assert story in stories