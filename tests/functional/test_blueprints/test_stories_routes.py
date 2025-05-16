import pytest
from flask import url_for

@pytest.fixture(autouse=True)
def push_app_context(app):
    ctx = app.app_context()
    ctx.push()
    yield
    ctx.pop()

@pytest.fixture
def stories_url_map():
    return {
        "add": "stories.add",
        "list": "stories.list",
    }

def test_add_story_get(client, stories_url_map):
    response = client.get(url_for(stories_url_map["add"]))
    assert response.status_code == 200
    assert b"Add Story" in response.data 

def test_add_story_post_success(client, stories_url_map, mocker, test_data):
    """Test POST /stories/add with valid data adds a story and flashes success."""
    mocker.patch("app.services.category_service.get_all_categories", return_value=[])
    mock_add_story = mocker.patch(
        "app.services.story_service.add_story_with_categories",
        return_value=42
    )
    data = {
        "story_content": "A new story",
        "new_category": "NewCat",
        "categories": [str(test_data["ids"]["categories"][0])]
    }
    response = client.post(
        url_for(stories_url_map["add"]),
        data=data,
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Story added successfully" in response.data
    mock_add_story.assert_called_once_with(
        "A new story",
        [test_data["ids"]["categories"][0]],
        "NewCat"
    )

def test_add_story_post_no_content(client, stories_url_map, mocker):
    """Test POST /stories/add with no content does not add a story."""
    mocker.patch("app.services.category_service.get_all_categories", return_value=[])
    mock_add_story = mocker.patch(
        "app.services.story_service.add_story_with_categories"
    )
    data = {
        "story_content": "",
        "new_category": "NewCat",
        "categories": ["1"]
    }
    response = client.post(
        url_for(stories_url_map["add"]),
        data=data,
        follow_redirects=True,
    )
    assert response.status_code == 200
    mock_add_story.assert_not_called()

def test_add_story_post_service_error(client, stories_url_map, mocker, test_data):
    """Test POST /stories/add when the service raises an exception."""
    mocker.patch("app.services.category_service.get_all_categories", return_value=[])
    mocker.patch(
        "app.services.story_service.add_story_with_categories",
        side_effect=Exception("Simulated DB error")
    )
    data = {
        "story_content": "A new story",
        "new_category": "NewCat",
        "categories": [str(test_data["ids"]["categories"][0])]
    }
    response = client.post(
        url_for(stories_url_map["add"]),
        data=data,
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Error adding story" in response.data
    assert b"Simulated DB error" in response.data

def test_list_stories_basic(client, test_data, stories_url_map, app):
    per_page = app.config["PER_PAGE"]
    response = client.get(url_for(stories_url_map["list"], page=1))
    print(response.data.decode())
    assert response.status_code == 200
    # Only the first `per_page` stories should be present
    for sid in list(reversed(test_data["ids"]["stories"]))[:per_page]: #newest stories are displayed at the top so it's the last 10 we expect.
        assert f'<td>{sid}</td>'.encode() in response.data
    for sid in list(reversed(test_data["ids"]["stories"]))[per_page:]:
        assert f'<td>{sid}</td>'.encode() not in response.data


def test_list_stories_template_filtering(client, stories_url_map, test_data):
    """Test GET /stories/list with template filtering."""
    with client.session_transaction() as sess:
        sess["template_ids"] = [str(tid) for tid in test_data["ids"]["templates"][:2]]
    response = client.get(url_for(stories_url_map["list"], source="templates", template_count=2))
    assert response.status_code == 200
    with client.session_transaction() as sess:
        assert sess["stories_source"] == "templates"
        assert sess["template_count"] == "2"

# def test_list_stories_search_filter(client, test_data, stories_url_map):
#     response = client.get(url_for(stories_url_map["list"], search_text="run"))
#     assert response.status_code == 200
#     # Only stories containing "cat" should appear
#     for story in test_data["objects"]["stories"]:
#         if "cat" in story.content:
#             assert story.content.encode() in response.data

def test_list_stories_search_filter(client, test_data, stories_url_map):
    response = client.get(url_for(stories_url_map["list"], search_text="run"))
    assert response.status_code == 200
    # Find stories that should match the search
    matching_ids = [str(story.story_id) for story in test_data["objects"]["stories"] if "run" in story.content]
    # Assert that only matching story IDs appear in the response
    for sid in matching_ids:
        assert sid.encode() in response.data

def test_list_stories_category_filter_valid(client, stories_url_map, test_data):
    """Test GET /stories/list with valid category_filter."""
    category_id = str(test_data["ids"]["categories"][0])
    response = client.get(url_for(stories_url_map["list"], category_filter=category_id))
    assert response.status_code == 200

def test_list_stories_category_filter_invalid(client, stories_url_map):
    """Test GET /stories/list with invalid category_filter triggers flash."""
    response = client.get(url_for(stories_url_map["list"], category_filter="not_an_int"))
    assert response.status_code == 200
    assert b"Invalid category filter" in response.data

def test_list_stories_sort_asc(client, stories_url_map):
    """Test GET /stories/list with ascending sort."""
    response = client.get(url_for(stories_url_map["list"], sort_by="asc"))
    assert response.status_code == 200

def test_list_stories_sort_desc(client, stories_url_map):
    """Test GET /stories/list with descending sort."""
    response = client.get(url_for(stories_url_map["list"], sort_by="desc"))
    assert response.status_code == 200

def test_list_stories_pagination(client, test_data, stories_url_map, app):
    per_page = app.config["PER_PAGE"] # needs to be set to the same value as the page? Is there a way to get this from the app?
    total_stories = len(test_data["ids"]["stories"])
    assert total_stories > per_page  # This should always be true if fixture is correct

    # Page 1 should have per_page stories
    response1 = client.get(url_for(stories_url_map["list"], page=1))
    assert response1.status_code == 200
    expected_page1 = min(per_page, total_stories)
    count_page1 = sum(1 for sid in test_data["ids"]["stories"][:per_page] if str(sid).encode() in response1.data)
    assert count_page1 == expected_page1

    # Page 3 should have the remainder, or 0 if too few stories or per_page if too large
    page = 3
    start = (page - 1) * per_page
    end = start + per_page
    expected_page3 = max(0, min(per_page, total_stories - start))
    response3 = client.get(url_for(stories_url_map["list"], page=page))
    assert response3.status_code == 200
    count_page3 = sum(1 for sid in test_data["ids"]["stories"][start:end] if str(sid).encode() in response3.data)
    assert count_page3 == expected_page3

def test_list_stories_selected_story_ids_and_template_count(client, stories_url_map):
    """Test GET /stories/list uses session story_ids and template_count."""
    with client.session_transaction() as sess:
        sess["story_ids"] = ["1", "2"]
        sess["template_count"] = 5
    response = client.get(url_for(stories_url_map["list"]))
    assert response.status_code == 200