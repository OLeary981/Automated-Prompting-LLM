import pytest
from flask import url_for


@pytest.fixture(autouse=True)
def push_app_context(app):
    ctx = app.app_context()
    ctx.push()
    yield
    ctx.pop()

@pytest.fixture
def prompts_url_map():
    return {
        "list": "prompts.list",
        "update_selection": "prompts.update_selection",
    }

def test_list_prompts_get(client, test_data, prompts_url_map):
    """Test GET /prompts/list returns the prompts list page."""
    response = client.get(url_for(prompts_url_map["list"]))
    assert response.status_code == 200
    # Optionally check for prompt content or filter options in response - could use logic from tets_stories_routes.py for this 
    # (but pagination won't be a big deal as not enough prompts)
 
def test_list_prompts_post_redirect(client, prompts_url_map):
    """Test POST /prompts/list redirects to GET with args."""
    response = client.post(url_for(prompts_url_map["list"]), data={"provider": "Test Provider"})
    # Should redirect (302 or 303)
    assert response.status_code in (302, 303)
    # Should redirect to the list endpoint
    assert url_for(prompts_url_map["list"], _external=False) in response.headers["Location"]

@pytest.mark.parametrize("param,value,label", [
    ("start_date", "not-a-date", "start date"),
    ("end_date", "not-a-date", "end date"),
])
def test_list_prompts_invalid_date_flash(client, prompts_url_map, param, value, label):
    """Test GET /prompts/list with invalid date flashes a warning."""
    url = url_for(prompts_url_map["list"], **{param: value})
    response = client.get(url, follow_redirects=True)
    assert b"Invalid %s format" % label.encode() in response.data

def test_list_prompts_with_filters(client, test_data, prompts_url_map):
    """Test GET /prompts/list with filters returns filtered results."""
    provider = "Test Provider"
    model = "Test Model"
    question_id = test_data["ids"]["questions"][0]
    story_id = test_data["ids"]["stories"][0]
    url = url_for(prompts_url_map["list"], provider=provider, model=model, question_id=question_id, story_id=story_id)
    response = client.get(url)
    assert response.status_code == 200
    # Optionally check for filtered content

def test_list_prompts_pagination(client, prompts_url_map):
    """Test GET /prompts/list with pagination params."""
    url = url_for(prompts_url_map["list"], page=1, per_page=1)
    response = client.get(url)
    assert response.status_code == 200

def test_update_selection_clear_all(client, prompts_url_map):
    """Test POST /prompts/update_selection with clear_all action."""
    with client.session_transaction() as sess:
        sess["prompt_ids"] = ["1", "2"]
    response = client.post(
        url_for(prompts_url_map["update_selection"]),
        json={"action": "clear_all"},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["selected_count"] == 0
    with client.session_transaction() as sess:
        assert sess["prompt_ids"] == []

def test_update_selection_select_multiple(client, prompts_url_map):
    """Test POST /prompts/update_selection with select_multiple action."""
    with client.session_transaction() as sess:
        sess["prompt_ids"] = ["1"]
    response = client.post(
        url_for(prompts_url_map["update_selection"]),
        json={"action": "select_multiple", "prompt_ids": ["2", "3"]},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert set(data["selected_ids"]) == {"1", "2", "3"}

def test_update_selection_invert_selection(client, prompts_url_map):
    """Test POST /prompts/update_selection with invert_selection action."""
    with client.session_transaction() as sess:
        sess["prompt_ids"] = ["1"]
    response = client.post(
        url_for(prompts_url_map["update_selection"]),
        json={"action": "invert_selection", "select_ids": ["2"], "deselect_ids": ["1"]},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert set(data["selected_ids"]) == {"2"}

def test_update_selection_toggle_add_and_remove(client, prompts_url_map):
    """Test POST /prompts/update_selection with toggle action (add and remove)."""
    # Add
    with client.session_transaction() as sess:
        sess["prompt_ids"] = ["1"]
    response = client.post(
        url_for(prompts_url_map["update_selection"]),
        json={"prompt_id": "2", "selected": True},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert set(data["selected_ids"]) == {"1", "2"}
    # Remove
    with client.session_transaction() as sess:
        sess["prompt_ids"] = ["1", "2"]
    response = client.post(
        url_for(prompts_url_map["update_selection"]),
        json={"prompt_id": "2", "selected": False},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert set(data["selected_ids"]) == {"1"}

def test_update_selection_invalid_request(client, prompts_url_map):
    """Test POST /prompts/update_selection without AJAX header returns 400."""
    response = client.post(
        url_for(prompts_url_map["update_selection"]),
        json={"action": "clear_all"},
    )
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
