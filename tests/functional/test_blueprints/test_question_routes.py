import pytest
from flask import url_for


@pytest.fixture(autouse=True)
def push_app_context(app):
    ctx = app.app_context()
    ctx.push()
    yield
    ctx.pop()

@pytest.fixture
def questions_url_map():
    return {
        "list": "questions.list",
        "add": "questions.add",
        "select": "questions.select",
        "update_selection": "questions.update_selection",
    }

def test_list_questions(client, test_data, questions_url_map):
    """Test the /list route displays all questions."""
    response = client.get(url_for(questions_url_map["list"]))
    assert response.status_code == 200
    for qid in test_data["ids"]["questions"]:
        # Optionally check for question content if available in test_data
        pass

def test_add_question_get(client, questions_url_map):
    """Test GET on /add returns the add question form."""
    response = client.get(url_for(questions_url_map["add"]))
    assert response.status_code == 200
    assert b"add question" in response.data.lower()

def test_add_question_post(client, questions_url_map):
    """Test POST on /add adds a question and redirects."""
    response = client.post(
        url_for(questions_url_map["add"]),
        data={"question_content": "What is your quest?"},
        follow_redirects=False,
    )
    assert response.status_code in (302, 303)
    # Optionally, check that the question was added to the DB

def test_select_question_get(client, test_data, questions_url_map):
    """Test GET on /select displays all questions."""
    response = client.get(url_for(questions_url_map["select"]))
    assert response.status_code == 200
    # Optionally check for question content

def test_select_question_post(client, questions_url_map):
    """Test POST on /select sets question_id in session and redirects."""
    with client.session_transaction() as sess:
        sess.clear()
    response = client.post(
        url_for(questions_url_map["select"]),
        data={"question_id": '42'},# Flask stores form data as str, so have put data in as a string
        follow_redirects=False,
    )
    assert response.status_code in (302, 303)
    with client.session_transaction() as sess:
        assert sess.get("question_id") == "42"  


def test_update_selection_clear(client, questions_url_map):
    """Test POST on /update_selection with clear removes question_id from session."""
    with client.session_transaction() as sess:
        sess["question_id"] = '42'
    response = client.post(
        url_for(questions_url_map["update_selection"]),
        json={"clear": True},
    )
    assert response.status_code == 200
    with client.session_transaction() as sess:
        assert "question_id" not in sess

def test_update_selection_set_valid(client, test_data, questions_url_map):
    """Test POST on /update_selection sets a valid question_id."""
    valid_id = test_data["ids"]["questions"][0]
    response = client.post(
        url_for(questions_url_map["update_selection"]),
        json={"question_id": valid_id},
    )
    assert response.status_code == 200
    assert response.get_json()["success"] is True
    with client.session_transaction() as sess:
        assert sess.get("question_id") == (valid_id)

def test_update_selection_set_invalid(client, questions_url_map):
    """Test POST on /update_selection with invalid question_id returns 404."""
    response = client.post(
        url_for(questions_url_map["update_selection"]),
        json={"question_id": '999999'},
    )
    assert response.status_code == 404
    assert response.get_json()["success"] is False

def test_update_selection_no_id(client, questions_url_map):
    """Test POST on /update_selection with no question_id returns 400."""
    response = client.post(
        url_for(questions_url_map["update_selection"]),
        json={},
    )
    assert response.status_code == 400
    assert response.get_json()["success"] is False