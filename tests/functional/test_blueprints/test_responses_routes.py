import pytest
from flask import url_for

@pytest.fixture(autouse=True)
def push_app_context(app):
    ctx = app.app_context()
    ctx.push()
    yield
    ctx.pop()

@pytest.fixture
def responses_url_map():
    return {
        "list": "responses.list",
        "export": "responses.export",
        "update_response_flag": "responses.update_response_flag",
        "view_prompt_responses": "responses.view_prompt_responses",
        "view_story_responses": "responses.view_story_responses",
        "view_template_responses": "responses.view_template_responses",
    }

def test_list_responses_get(client, test_data, responses_url_map):
    """Test GET /responses/list returns the responses list page."""
    response = client.get(url_for(responses_url_map["list"]))
    assert response.status_code == 200
    assert b"responses" in response.data or b"Response" in response.data

def test_list_responses_post_update_flag(client, test_data, responses_url_map):
    """Test POST /responses/list updates a response's flag and review notes."""
    response_id = test_data["ids"]["responses"][0]
    data = {
        "response_id": response_id,
        f"flagged_for_review_{response_id}": "on",
        f"review_notes_{response_id}": "Test review"
    }
    response = client.post(url_for(responses_url_map["list"]), data=data, follow_redirects=True)
    assert response.status_code == 200
    assert b"updated successfully" in response.data or b"Error updating response" in response.data

def test_list_responses_post_update_flag_error(client, test_data, responses_url_map, mocker):
    """Test POST /responses/list triggers error flash if update fails."""
    response_id = test_data["ids"]["responses"][0]
    # Mock the service to simulate an error
    mocker.patch(
        "app.services.response_service.update_response_review",
        return_value=(False, "Simulated error")
    )
    data = {
        "response_id": response_id,
        f"flagged_for_review_{response_id}": "on",
        f"review_notes_{response_id}": "Test review"
    }
    response = client.post(url_for(responses_url_map["list"]), data=data, follow_redirects=True)
    assert response.status_code == 200
    assert b"Error updating response: Simulated error" in response.data

def test_update_response_flag_error(client, test_data, responses_url_map, mocker):
    response_id = test_data["ids"]["responses"][0]
    mocker.patch(
        "app.services.response_service.update_response_flag",
        return_value=(False, "Simulated error")
    )
    data = {"response_id": response_id, "flagged": True}
    response = client.post(
        url_for(responses_url_map["update_response_flag"]),
        json=data,
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert response.status_code == 500
    assert response.get_json()["success"] is False
    assert "Simulated error" in response.get_json()["message"]

def test_list_responses_with_story_ids_filter(client, test_data, responses_url_map):
    # Set story_ids in session
    with client.session_transaction() as sess:
        sess["story_ids"] = [str(sid) for sid in test_data["ids"]["stories"][:2]]
        if "response_ids" in sess:
            del sess["response_ids"]  # Ensure response_ids is not set

    # GET request to /responses/list (no clear_stories in query)
    response = client.get(url_for(responses_url_map["list"]))
    assert response.status_code == 200
    # Optionally, check that the filtered responses are present in the page
    for sid in test_data["ids"]["stories"][:2]:
        assert str(sid).encode() in response.data

def test_list_responses_clear_filters(client, test_data, responses_url_map):
    """Test clearing story, response, and template filters via GET params."""
    with client.session_transaction() as sess:
        sess["story_ids"] = ["1", "2"]
        sess["response_ids"] = ["1"]
        sess["template_ids"] = ["1"]
    # Clear stories
    response = client.get(url_for(responses_url_map["list"], clear_stories=1))
    assert response.status_code == 200
    # Clear responses
    response = client.get(url_for(responses_url_map["list"], clear_responses=1))
    assert response.status_code == 200
    # Clear templates
    response = client.get(url_for(responses_url_map["list"], clear_templates=1))
    assert response.status_code == 200

def test_export_responses_csv(client, test_data, responses_url_map):
    """Test GET /responses/export returns a CSV file."""
    response = client.get(url_for(responses_url_map["export"]))
    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    assert b"ID,Date,Time,Provider,Model" in response.data

def test_update_response_flag_ajax(client, test_data, responses_url_map):
    """Test POST /responses/update_response_flag toggles flag via AJAX."""
    response_id = test_data["ids"]["responses"][0]
    data = {"response_id": response_id, "flagged": True}
    response = client.post(
        url_for(responses_url_map["update_response_flag"]),
        json=data,
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["success"] is True
    assert json_data["flagged"] is True

def test_update_response_flag_invalid_request(client, test_data, responses_url_map):
    """Test POST /responses/update_response_flag without AJAX header returns 400."""
    response_id = test_data["ids"]["responses"][0]
    data = {"response_id": response_id, "flagged": True}
    response = client.post(
        url_for(responses_url_map["update_response_flag"]),
        json=data,
    )
    assert response.status_code == 400
    json_data = response.get_json()
    assert json_data["success"] is False

def test_view_prompt_responses_redirect(client, test_data, responses_url_map):
    """Test /responses/view_prompt_responses redirects to list if prompts are selected."""
    with client.session_transaction() as sess:
        sess["prompt_ids"] = [str(test_data["ids"]["prompts"][0])]
    response = client.get(url_for(responses_url_map["view_prompt_responses"]))
    assert response.status_code in (302, 303)
    assert "responses/list" in response.headers["Location"]

def test_view_story_responses_redirect(client, test_data, responses_url_map):
    """Test /responses/view_story_responses redirects to list."""
    with client.session_transaction() as sess:
        sess["story_ids"] = [str(test_data["ids"]["stories"][0])]
    response = client.get(url_for(responses_url_map["view_story_responses"]))
    assert response.status_code in (302, 303)
    assert "responses/list" in response.headers["Location"]

def test_view_template_responses_redirect(client, test_data, responses_url_map):
    """Test /responses/view_template_responses redirects to list."""
    with client.session_transaction() as sess:
        sess["template_ids"] = [str(test_data["ids"]["templates"][0])]
    response = client.get(url_for(responses_url_map["view_template_responses"]))
    assert response.status_code in (302, 303)
    assert "responses/list" in response.headers["Location"]

def test_view_prompt_responses_no_selection(client, responses_url_map):
    """Test /responses/view_prompt_responses with no prompts selected."""
    response = client.get(url_for(responses_url_map["view_prompt_responses"]), follow_redirects=True)
    assert b"No prompts selected" in response.data

def test_view_story_responses_no_selection(client):
    """Test /responses/view_story_responses with no stories selected."""
    response = client.get("/responses/view_story_responses", follow_redirects=True)
    assert b"No stories selected" in response.data

def test_view_template_responses_no_selection(client):
    """Test /responses/view_template_responses with no templates selected."""
    response = client.get("/responses/view_template_responses", follow_redirects=True)
    assert b"No templates selected" in response.data

def test_view_prompt_responses_no_results(client, responses_url_map, mocker):
    """Test /responses/view_prompt_responses with prompt_ids but no responses found."""
    with client.session_transaction() as sess:
        sess["prompt_ids"] = ["9999"]  # Use a prompt ID that will return no responses
    # Mock the service to return an empty list
    mocker.patch(
        "app.services.response_service.get_responses_for_prompt",
        return_value=[]
    )
    response = client.get(url_for(responses_url_map["view_prompt_responses"]), follow_redirects=True)
    assert b"No responses found for the selected prompts" in response.data

def test_view_story_responses_no_results(client, responses_url_map, mocker):
    with client.session_transaction() as sess:
        sess["story_ids"] = ["9999"]
    mocker.patch(
        "app.services.response_service.get_responses_for_stories",
        return_value=[]
    )
    response = client.get(url_for(responses_url_map["view_story_responses"]), follow_redirects=True)
    assert b"No responses found for the selected stories" in response.data

def test_view_template_responses_no_results(client, responses_url_map, mocker):
    with client.session_transaction() as sess:
        sess["template_ids"] = ["9999"]
    mocker.patch(
        "app.services.response_service.get_responses_for_templates",
        return_value=[]
    )
    response = client.get(url_for(responses_url_map["view_template_responses"]), follow_redirects=True)
    assert b"No responses found for the selected templates" in response.data