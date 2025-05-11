import pytest
from flask import url_for
import json

@pytest.fixture(autouse=True)
def push_app_context(app):
    ctx = app.app_context()
    ctx.push()
    yield
    ctx.pop()

@pytest.fixture
def templates_url_map():
    return {
        "list": "templates.list",
        "add": "templates.add",
        "update_template_selection": "templates.update_template_selection",
        "generate_stories": "templates.generate_stories",
        "display_generated_stories": "templates.display_generated_stories",
        "add_word": "templates.add_word",
        "delete_word": "templates.delete_word",
    }

def test_list_templates(client, test_data, templates_url_map):
    """Test GET /templates/list returns the templates list page."""
    response = client.get(url_for(templates_url_map["list"]))
    assert response.status_code == 200
    for tid in test_data["ids"]["templates"]:
        assert str(tid).encode() in response.data

def test_add_template_post(client, templates_url_map):
    """Test POST /templates/add adds a template and redirects."""
    response = client.post(
        url_for(templates_url_map["add"]),
        data={"template_content": "Test template content"},
        follow_redirects=False,
    )
    assert response.status_code in (302, 303)

def test_update_template_selection_clear(client, templates_url_map):
    """Test POST /update_template_selection with clear_all removes template_ids from session."""
    with client.session_transaction() as sess:
        sess["template_ids"] = ["1", "2"]
    response = client.post(
        url_for(templates_url_map["update_template_selection"]),
        json={"action": "clear_all"},
    )
    assert response.status_code == 200
    with client.session_transaction() as sess:
        assert sess.get("template_ids") == []

def test_update_template_selection_toggle(client, templates_url_map):
    """Test POST /update_template_selection toggles a template selection."""
    with client.session_transaction() as sess:
        sess["template_ids"] = []
    response = client.post(
        url_for(templates_url_map["update_template_selection"]),
        json={"template_id": "42", "selected": True},
    )
    assert response.status_code == 200
    assert response.get_json()["success"] is True
    with client.session_transaction() as sess:
        assert "42" in sess.get("template_ids", [])

def test_update_template_selection_select_multiple(client, templates_url_map, test_data):
    """Test POST /update_template_selection with select_multiple adds multiple template_ids."""
    with client.session_transaction() as sess:
        sess["template_ids"] = []
    template_ids = [str(tid) for tid in test_data["ids"]["templates"][:2]]
    response = client.post(
        url_for(templates_url_map["update_template_selection"]),
        json={"action": "select_multiple", "template_ids": template_ids},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert set(data["selected_ids"]) == set(template_ids)
    with client.session_transaction() as sess:
        assert set(sess["template_ids"]) == set(template_ids)

def test_update_template_selection_unselect(client, templates_url_map, test_data):
    """Test POST /update_template_selection unselects a template."""
    template_id = str(test_data["ids"]["templates"][0])
    # First, add the template to the session
    with client.session_transaction() as sess:
        sess["template_ids"] = [template_id]
    # Now, unselect it
    response = client.post(
        url_for(templates_url_map["update_template_selection"]),
        json={"template_id": template_id, "selected": False},
    )
    assert response.status_code == 200
    assert response.get_json()["success"] is True
    with client.session_transaction() as sess:
        assert template_id not in sess.get("template_ids", [])

def test_generate_stories_get(client, templates_url_map):
    """Test GET /templates/generate_stories returns the form."""
    response = client.get(url_for(templates_url_map["generate_stories"]))
    assert response.status_code == 200
    assert b"template" in response.data or b"Template" in response.data

def test_generate_stories_post_generate(client, templates_url_map, mocker, test_data):
    """Test POST /generate_stories with 'generate' and real field data."""
    # Use a real template from test_data
    template_id = str(test_data["ids"]["templates"][0])
    # Build field_data for the template's fields
    field_data = {
        "animal": ["cat", "dog"],
        "action": ["run", "jump"]
    }
    mocker.patch(
        "app.services.story_builder_service.generate_stories",
        return_value=[1, 2, 3]
    )
    with client.session_transaction() as sess:
        sess["template_id"] = template_id
    response = client.post(
        url_for(templates_url_map["generate_stories"]),
        data={
            "generate": "1",
            "field_data": json.dumps(field_data),
            "template_id": template_id,
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Stories generated successfully" in response.data

def test_generate_stories_post_no_template_selected(client, templates_url_map):
    """Test POST /generate_stories with no template_id flashes error and redirects."""
    response = client.post(
        url_for(templates_url_map["generate_stories"]),
        data={"generate": "1", "field_data": "{}"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"No template selected" in response.data

def test_generate_stories_post_selected_categories(client, templates_url_map, mocker, test_data):
    """Test POST /generate_stories with valid and invalid category IDs."""
    template_id = str(test_data["ids"]["templates"][0])
    mocker.patch("app.services.story_builder_service.generate_stories", return_value=[1])
    mocker.patch("app.services.story_builder_service.update_field_words", return_value=None)
    # Patch add_category to avoid DB ops
    mocker.patch("app.services.category_service.add_category", return_value=999)
    with client.session_transaction() as sess:
        sess["template_id"] = template_id
    response = client.post(
        url_for(templates_url_map["generate_stories"]),
        data={
            "generate": "1",
            "field_data": "{}",
            "template_id": template_id,
            "story_categories": ["1", "not_an_int"],  # One valid, one invalid
            "new_categories": "",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Stories generated successfully" in response.data

def test_generate_stories_post_new_category_success(client, templates_url_map, mocker, test_data):
    """Test POST /generate_stories with new category successfully added."""
    template_id = str(test_data["ids"]["templates"][0])
    # Patch add_category to return a known ID
    mock_add_category = mocker.patch("app.services.category_service.add_category", return_value=123)
    # Patch generate_stories to capture category_ids
    called = {}
    def fake_generate_stories(template_id_arg, field_data_arg, category_ids_arg=None):
        called["category_ids"] = category_ids_arg
        return [1]
    mocker.patch("app.services.story_builder_service.generate_stories", side_effect=fake_generate_stories)
    mocker.patch("app.services.story_builder_service.update_field_words", return_value=None)
    with client.session_transaction() as sess:
        sess["template_id"] = template_id
    response = client.post(
        url_for(templates_url_map["generate_stories"]),
        data={
            "generate": "1",
            "field_data": "{}",
            "template_id": template_id,
            "story_categories": [],
            "new_categories": "NewCat",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    # Check that add_category was called and its return value is in category_ids
    mock_add_category.assert_called_once_with("NewCat")
    assert called["category_ids"] == [123]
    assert b"Stories generated successfully" in response.data

def test_generate_stories_post_new_category_exception(client, templates_url_map, mocker, test_data, capsys):
    """Test POST /generate_stories with new category that raises exception."""
    template_id = str(test_data["ids"]["templates"][0])
    mocker.patch("app.services.story_builder_service.generate_stories", return_value=[1])
    mocker.patch("app.services.story_builder_service.update_field_words", return_value=None)
    mocker.patch("app.services.category_service.add_category", side_effect=Exception("DB error"))
    with client.session_transaction() as sess:
        sess["template_id"] = template_id
    response = client.post(
        url_for(templates_url_map["generate_stories"]),
        data={
            "generate": "1",
            "field_data": "{}",
            "template_id": template_id,
            "story_categories": [],
            "new_categories": "NewCat",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200    
    assert b"Could not add category" in response.data
    assert b"DB error" in response.data
    assert b"Stories generated successfully" in response.data

def test_generate_stories_post_generate_exception(client, templates_url_map, mocker, test_data):
    """Test POST /generate_stories handles exception and flashes error."""
    template_id = str(test_data["ids"]["templates"][0])
    mocker.patch(
        "app.services.story_builder_service.generate_stories",
        side_effect=Exception("Simulated generation error")
    )
    mocker.patch(
        "app.services.story_builder_service.update_field_words",
        return_value=None
    )
    with client.session_transaction() as sess:
        sess["template_id"] = template_id
    response = client.post(
        url_for(templates_url_map["generate_stories"]),
        data={
            "generate": "1",
            "field_data": "{}",
            "template_id": template_id,
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Error generating stories" in response.data
    assert b"Simulated generation error" in response.data

def test_generate_stories_post_update_fields(client, templates_url_map, mocker, test_data):
    """Test POST /templates/generate_stories with 'update_fields'."""
    mocker.patch(
        "app.services.story_builder_service.update_field_words",
        return_value=None
    )
    template_id = str(test_data["ids"]["templates"][0])
    field_data = {
        "animal": ["cat", "dog"],
        "action": ["run", "jump"]
    }
    with client.session_transaction() as sess:
        sess["template_id"] = template_id
    response = client.post(
        url_for(templates_url_map["generate_stories"]),
        data={
            "update_fields": "1",
            "field_data": json.dumps(field_data),
            "template_id": template_id,
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Fields updated successfully" in response.data

def test_display_generated_stories(client, templates_url_map, mocker):
    """Test GET /templates/display_generated_stories shows generated stories."""
    with client.session_transaction() as sess:
        sess["generated_story_ids"] = [1, 2]
    mocker.patch(
        "app.services.story_service.get_story_by_id",
        side_effect=lambda sid: type("Story", (), {"id": sid, "content": f"Story {sid}"})()
    )
    response = client.get(url_for(templates_url_map["display_generated_stories"]))
    assert response.status_code == 200
    assert b"Story 1" in response.data or b"Story 2" in response.data

def test_add_word_ajax(client, templates_url_map, mocker):
    """Test POST /templates/add_word via AJAX."""
    mocker.patch(
        "app.services.story_builder_service.add_words_to_field",
        return_value=None
    )
    response = client.post(
        url_for(templates_url_map["add_word"]),
        json={"field_name": "animal", "new_words": ["cat", "dog"]},
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 200
    assert response.get_json()["success"] is True

def test_add_word_form(client, templates_url_map, mocker):
    """Test POST /templates/add_word via form."""
    mocker.patch(
        "app.services.story_builder_service.add_words_to_field",
        return_value=None
    )
    response = client.post(
        url_for(templates_url_map["add_word"]),
        data={"field_name": "animal", "new_words": "cat,dog", "template_id": "1"},
        follow_redirects=False,
    )
    assert response.status_code in (302, 303)

def test_delete_word_ajax(client, templates_url_map, mocker):
    """Test POST /templates/delete_word via AJAX."""
    mocker.patch(
        "app.services.story_builder_service.delete_word_from_field",
        return_value=True
    )
    response = client.post(
        url_for(templates_url_map["delete_word"]),
        json={"field_name": "animal", "word": "cat"},
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 200
    assert response.get_json()["success"] is True

def test_delete_word_ajax_error(client, templates_url_map, mocker):
    """Test POST /templates/delete_word error handling."""
    mocker.patch(
        "app.services.story_builder_service.delete_word_from_field",
        side_effect=Exception("Simulated error")
    )
    response = client.post(
        url_for(templates_url_map["delete_word"]),
        json={"field_name": "animal", "word": "cat"},
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 500
    assert b"Simulated error" in response.data

def test_add_word_ajax_error(client, templates_url_map, mocker):
    """Test POST /templates/add_word via AJAX with error."""
    mocker.patch(
        "app.services.story_builder_service.add_words_to_field",
        side_effect=Exception("Simulated add error")
    )
    response = client.post(
        url_for(templates_url_map["add_word"]),
        json={"field_name": "animal", "new_words": ["cat", "dog"]},
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 500
    assert response.get_json()["success"] is False
    assert "Simulated add error" in response.get_json()["message"]

def test_delete_word_ajax_invalid(client, templates_url_map):
    """Test POST /templates/delete_word with invalid data."""
    response = client.post(
        url_for(templates_url_map["delete_word"]),
        json={"field_name": "animal"},
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400
    assert b"Invalid data provided" in response.data

def test_add_word_ajax_missing_fields(client, templates_url_map):
    """Test POST /templates/add_word via AJAX with missing required fields returns 400."""
    # Missing both field_name and new_words
    response = client.post(
        url_for(templates_url_map["add_word"]),
        json={},  # Empty JSON triggers the missing fields branch
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400
    assert response.get_json()["success"] is False
    assert "Missing required fields" in response.get_json()["message"]

    # Missing only new_words
    response = client.post(
        url_for(templates_url_map["add_word"]),
        json={"field_name": "animal"},
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400
    assert response.get_json()["success"] is False
    assert "Missing required fields" in response.get_json()["message"]

    # Missing only field_name
    response = client.post(
        url_for(templates_url_map["add_word"]),
        json={"new_words": ["cat", "dog"]},
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400
    assert response.get_json()["success"] is False
    assert "Missing required fields" in response.get_json()["message"]

def test_generate_stories_get_sets_template_id_from_query(client, templates_url_map, test_data):
    """Test GET /generate_stories?template_id=... sets session['template_id']."""
    template_id = str(test_data["ids"]["templates"][0])
    with client.session_transaction() as sess:
        sess.pop("template_id", None)
    response = client.get(
        url_for(templates_url_map["generate_stories"], template_id=template_id)
    )
    assert response.status_code == 200
    with client.session_transaction() as sess:
        assert sess["template_id"] == template_id

