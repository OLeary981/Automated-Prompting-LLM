import pytest
import werkzeug
from app.services import story_builder_service
from app.models import Template, Story, Field, Word, StoryCategory, Category

class TestStoryBuilderService:

    # def test_get_all_templates(self, session, test_data):
    #     """Test get_all_templates returns all templates."""
    #     templates = story_builder_service.get_all_templates()
    #     # Should include at least the templates from test_data
    #     ids = [t.template_id for t in templates]
    #     for tid in test_data["ids"]["templates"]:
    #         assert tid in ids

    # def test_get_all_templates(self, session, test_data):
    #     """Test retrieval of all templates."""
    #     templates = story_builder_service.get_all_templates()
    #     assert len(templates) >= 2  # At least those from test_data
    #     assert any(t.content == "This is a {animal} template with {action}." for t in templates)


#combination of the logic in both tests that are commented out.
    def test_get_all_templates(self, session, test_data):
        """Test get_all_templates returns all templates and expected content."""
        templates = story_builder_service.get_all_templates()
        ids = [t.template_id for t in templates]
        for tid in test_data["ids"]["templates"]:
            assert tid in ids
        assert len(templates) >= 2  # At least those from test_data
        assert any(t.content == "This is a {animal} template with {action}." for t in templates)

    def test_get_all_field_names(self, session, test_data):
        """Test get_all_field_names returns all field names as strings."""
        field_names = story_builder_service.get_all_field_names()
        for field_name in test_data["ids"]["fields"]:
            assert field_name in field_names

    def test_get_template_by_id(self, session, test_data):
        """Test get_template_by_id returns the correct template."""
        tid = test_data["ids"]["templates"][0]
        template = story_builder_service.get_template_by_id(tid)
        assert template is not None
        assert template.template_id == tid

#Don't need this as it is in the story_service.py file, so commeted out in story_builder_service.py
    # def test_get_story_by_id(self, session, test_data):
    #     """Test get_story_by_id returns the correct story."""
    #     sid = test_data["ids"]["stories"][0]
    #     story = story_builder_service.get_story_by_id(sid)
    #     assert story is not None
    #     assert story.story_id == sid

    def test_get_templates_filtered(self, session, test_data):
        """Test get_templates_filtered filters and sorts templates correctly."""
        # No filter, default sort (desc)
        templates = story_builder_service.get_templates_filtered()
        assert len(templates) >= 2  # At least those from test_data
        # Should be sorted by template_id descending
        ids = [t.template_id for t in templates]
        assert ids == sorted(ids, reverse=True)

        # Filter by search_text
        templates_with_cat = story_builder_service.get_templates_filtered(search_text="cat")
        assert any("cat" in t.content for t in templates_with_cat)
        # Should not include templates without "cat"
        assert all("cat" in t.content or "Cat" in t.content for t in templates_with_cat)

        # Ascending sort
        templates_asc = story_builder_service.get_templates_filtered(sort_by="asc")
        ids_asc = [t.template_id for t in templates_asc]
        assert ids_asc == sorted(ids_asc)

    def test_add_template(self, session):
        """Test add_template adds a new template and returns its ID."""
        content = "A new {field} template."
        tid = story_builder_service.add_template(content)
        template = session.get(Template, tid)
        assert template is not None
        assert template.content == content



    def test_get_template_fields(self, session, test_data):
        """Test extraction of fields and missing fields from a template."""
        template_id = test_data["ids"]["templates"][0]
        fields, missing = story_builder_service.get_template_fields(template_id)
        assert "animal" in fields
        assert "action" in fields
        assert isinstance(fields["animal"], list)
        assert isinstance(missing, list)

    def test_add_words_to_field_new_and_existing(self, session):
        """Test adding new words to a new and existing field."""
        # Add to a new field
        field_name = "weather"
        new_words = "sunny, rainy"
        story_builder_service.add_words_to_field(field_name, new_words)
        field = session.query(Field).filter_by(field=field_name).first()
        assert field is not None
        assert set(w.word for w in field.words) == {"sunny", "rainy"}

        # Add to an existing field (should not duplicate)
        story_builder_service.add_words_to_field(field_name, "sunny, cloudy")
        field = session.query(Field).filter_by(field=field_name).first()
        assert set(w.word for w in field.words) == {"sunny", "rainy", "cloudy"}

    def test_delete_word_from_field(self, session):
        """Test deleting a word from a field and DB if not used elsewhere."""
        # Setup: create field and word
        field = Field(field="testfield")
        word = Word(word="testword")
        field.words.append(word)
        session.add(field)
        session.commit()

        # Delete the word from the field
        result = story_builder_service.delete_word_from_field("testfield", "testword")
        assert result is True
        # Word should be deleted from DB
        assert session.query(Word).filter_by(word="testword").first() is None

    def test_delete_word_from_field_still_used(self, session):
        """Test deleting a word from one field but not from DB if used elsewhere."""
        field1 = Field(field="field1")
        field2 = Field(field="field2")
        word = Word(word="sharedword")
        field1.words.append(word)
        field2.words.append(word)
        session.add_all([field1, field2])
        session.commit()

        # Remove from field1, should still exist
        result = story_builder_service.delete_word_from_field("field1", "sharedword")
        assert result is True
        assert session.query(Word).filter_by(word="sharedword").first() is not None

    def test_generate_permutations(self):
        """Test generating all permutations of field values."""
        fields = {"animal": ["cat", "dog"], "action": ["run", "jump"]}
        perms = story_builder_service.generate_permutations(fields)
        assert ("cat", "run") in perms
        assert ("dog", "jump") in perms
        assert len(perms) == 4

    # def test_generate_story_permutations(self):
    #     """Test generating all possible story permutations from template and field data."""
    #     template = "The {color} {animal} likes to {action}."
    #     field_data = {
    #         "color": ["red", "blue"],
    #         "animal": ["cat"],
    #         "action": ["jump", "run"]
    #     }
    #     stories = story_builder_service.generate_story_permutations(template, field_data)
    #     assert "The red cat likes to jump." in stories
    #     assert "The blue cat likes to run." in stories
    #     assert len(stories) == 4

    def test_update_field_words(self, session):
        """Test updating field words based on user selection."""
        field_data = {"mood": ["happy", "sad"]}
        story_builder_service.update_field_words(field_data)
        field = session.query(Field).filter_by(field="mood").first()
        assert field is not None
        assert set(w.word for w in field.words) == {"happy", "sad"}

    def test_template_filler_and_generate_stories(self, session, test_data):
        """Test filling a template and generating stories with categories."""
        template_id = test_data["ids"]["templates"][0]
        template = session.get(Template, template_id)
        field_data = {"animal": ["cat"], "action": ["run"]}
        # Add a category for association
        category_id = test_data["ids"]["categories"][0]
        story_ids = story_builder_service.generate_stories(template_id, field_data, [category_id])
        assert len(story_ids) == 1
        story = session.get(Story, story_ids[0])
        assert "cat" in story.content and "run" in story.content
        # Check category association
        sc = session.query(StoryCategory).filter_by(story_id=story.story_id, category_id=category_id).first()
        assert sc is not None

    def test_template_filler_missing_field_with_no_words(self, session, test_data):
        """Test template_filler uses default for a field with no words in DB."""
        template_id = test_data["ids"]["templates"][2]  # template3
        # Only provide object field data, omit 'no_words_field'
        field_data = {"object": ["table"]}
        story_ids = story_builder_service.generate_stories(template_id, field_data)
        for story_id in story_ids:
            story = session.get(Story, story_id)
            assert "[No value provided]" in story.content
            assert "table" in story.content

    def test_generate_stories_invalid_template(self, app):
        """Test generate_stories raises NotFound for missing template."""
        with app.app_context():
            with pytest.raises(werkzeug.exceptions.NotFound):
                story_builder_service.generate_stories(999999, {"animal": ["cat"]})

    
    def test_delete_word_from_field_prints_and_returns_true(self, session, capfd):
        """Test print output and return value for delete_word_from_field."""
        field = Field(field="testfield")
        word = Word(word="testword")
        field.words.append(word)
        session.add(field)
        session.commit()
        result = story_builder_service.delete_word_from_field("testfield", "testword")
        out, err = capfd.readouterr()
        assert "Successfully removed word 'testword' from field 'testfield'" in out
        assert result is True

    def test_delete_word_from_field_word_still_used_print(self, session, capfd):
        """Test print output when word is still used in another field."""
        field1 = Field(field="field1")
        field2 = Field(field="field2")
        word = Word(word="sharedword")
        field1.words.append(word)
        field2.words.append(word)
        session.add_all([field1, field2])
        session.commit()
        result = story_builder_service.delete_word_from_field("field1", "sharedword")
        out, err = capfd.readouterr()
        assert "is still associated with" in out
        assert result is True

    def test_update_field_words_returns_true(self, session):
        """Test update_field_words returns True."""
        field_data = {"emotion": ["happy", "sad"]}
        result = story_builder_service.update_field_words(field_data)
        assert result is True

    def test_template_filler_input_branch(self, session, monkeypatch):
        """Test the input() branch of template_filler for command-line usage."""
        # Create a template with a missing field
        from app.models import Template
        template = Template(content="The {missing} is here.")
        session.add(template)
        session.commit()
        template_id = template.template_id

        # Patch input to simulate user entering "foo,bar"
        monkeypatch.setattr("builtins.input", lambda prompt: "foo,bar")
        # Call template_filler with no field_data to trigger input branch
        ids = story_builder_service.template_filler(template, template_id)
        # Should generate two stories: "The foo is here." and "The bar is here."
        from app.models import Story
        stories = session.query(Story).filter(Story.story_id.in_(ids)).all()
        contents = [s.content for s in stories]
        assert "The foo is here." in contents
        assert "The bar is here." in contents

    def test_template_filler_input_branch_default(self, session, monkeypatch):
        """Test the input() branch of template_filler with empty input (default)."""
        from app.models import Template
        template = Template(content="The {missing} is here.")
        session.add(template)
        session.commit()
        template_id = template.template_id

        # Patch input to simulate user pressing enter (empty input)
        monkeypatch.setattr("builtins.input", lambda prompt: "")
        ids = story_builder_service.template_filler(template, template_id)
        from app.models import Story
        stories = session.query(Story).filter(Story.story_id.in_(ids)).all()
        assert any("default" in s.content for s in stories)

    def test_add_existing_word_to_new_field(self, session):
    # Create an existing word not linked to the target field
        word = Word(word="testword")
        session.add(word)
        session.commit()

        # Ensure word is not yet linked to "newfield"
        field_name = "newfield"
        story_builder_service.add_words_to_field(field_name, "testword")

        field = session.query(Field).filter_by(field=field_name).first()
        assert field is not None
        assert any(w.word == "testword" for w in field.words)

    def test_delete_word_from_field_field_not_found(self, session):
        with pytest.raises(ValueError, match="Field 'nonexistent' not found"):
            story_builder_service.delete_word_from_field("nonexistent", "anyword")

    def test_delete_word_from_field_word_not_found(self, session):
        # Create a field, but not the word
        field = Field(field="field_exists")
        session.add(field)
        session.commit()

        with pytest.raises(ValueError, match="Word 'missingword' not found"):
            story_builder_service.delete_word_from_field("field_exists", "missingword")
    
    def test_delete_word_from_field_word_not_in_field(self, session):
        # Create field and word separately, no association
        field = Field(field="field1")
        word = Word(word="lonelyword")
        session.add_all([field, word])
        session.commit()

        with pytest.raises(ValueError, match="is not associated with field"):
            story_builder_service.delete_word_from_field("field1", "lonelyword")

    # def test_generate_story_permutations_missing_field(self):
    #     template = "The {animal} jumps over the {object}."
    #     field_data = {"animal": ["cat"]}  # 'object' missing
    #     with pytest.raises(ValueError, match="Field 'object' has no values assigned"):
    #         story_builder_service.generate_story_permutations(template, field_data)
    
    def test_update_field_words_with_existing_word(self, session):
        # Add a word first
        word = Word(word="excited")
        session.add(word)
        session.commit()

        field_data = {"emotion": ["excited"]}
        result = story_builder_service.update_field_words(field_data)

        assert result is True
        field = session.query(Field).filter_by(field="emotion").first()
        assert field is not None
        assert any(w.word == "excited" for w in field.words)