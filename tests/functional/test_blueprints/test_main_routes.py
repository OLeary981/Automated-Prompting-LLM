import pytest

def test_clear_session_full(client):
    # Set up session data
    with client.session_transaction() as sess:
        sess['story_ids'] = [1, 2, 3]
        sess['question_id'] = 42
        sess['model'] = 'Test Model'
        sess['parameters'] = {'temperature': 0.7}
    # Call the route with clear_all
    response = client.get('/clear_session?clear_all=true', follow_redirects=True)
    assert response.status_code == 200 or response.status_code == 302
    # Check that session is cleared
    with client.session_transaction() as sess:
        assert 'story_ids' not in sess
        assert 'question_id' not in sess
        assert 'model' not in sess
        assert 'parameters' not in sess

#Commented out now that I have a parameterized test for selective clearing
# def test_clear_session_selective_story(client):
#     # Set up session data
#     with client.session_transaction() as sess:
#         sess['story_ids'] = [1, 2, 3]
#         sess['question_id'] = 42
#     # Call the route to clear only story_ids
#     response = client.get('/clear_session?clear_stories=true', follow_redirects=True)
#     assert response.status_code == 200 or response.status_code == 302
#     # Check that only story_ids is cleared
#     with client.session_transaction() as sess:
#         assert 'story_ids' not in sess
#         assert 'question_id' in sess

# def test_clear_session_selective_question(client):
#     # Set up session data
#     with client.session_transaction() as sess:
#         sess['story_ids'] = [1, 2, 3]
#         sess['question_id'] = 42
#     # Call the route to clear only question_id
#     response = client.get('/clear_session?clear_question=true', follow_redirects=True)
#     assert response.status_code == 200 or response.status_code == 302
#     # Check that only question_id is cleared
#     with client.session_transaction() as sess:
#         assert 'question_id' not in sess
#         assert 'story_ids' in sess

def test_clear_session_cancels_jobs(client, dummy_job):
    response = client.get('/clear_session?clear_all=true', follow_redirects=True)
    assert response.status_code in (200, 302)
    from app.services import async_service
    assert async_service.processing_jobs == {}
    assert dummy_job._cancelled is True



ALL_SESSION_KEYS = {
    'story_ids': [1, 2, 3],
    'question_id': 42,
    'model': 'Test Model',
    'provider': 'Test Provider',
    'model_id': 123,
    'parameters': {'temperature': 0.7},
    'stories_source': 'source',
    'template_ids': [10, 11],
}

@pytest.mark.parametrize("param,session_keys_to_clear", [
    ("clear_stories", ["story_ids"]),
    ("clear_question", ["question_id"]),
    ("clear_model", ["model", "provider", "model_id"]),
    ("clear_parameters", ["parameters"]),
    ("stories_source", ["stories_source"]),
    ("clear_templates", ["template_ids"]),
])
def test_clear_session_selective_keys(client, param, session_keys_to_clear):
    # Set up all session data
    with client.session_transaction() as sess:
        for key, value in ALL_SESSION_KEYS.items():
            sess[key] = value

    # Call the route to clear only the target key(s)
    response = client.get(f'/clear_session?{param}=true', follow_redirects=True)
    assert response.status_code in (200, 302)

    # Check that only the target key(s) are cleared, others remain
    with client.session_transaction() as sess:
        for key in session_keys_to_clear:
            assert key not in sess
        for key in ALL_SESSION_KEYS:
            if key not in session_keys_to_clear:
                assert key in sess
                assert sess[key] == ALL_SESSION_KEYS[key]


def test_clear_session_job_cancel_exception(client, dummy_job_exception):
    response = client.get('/clear_session?clear_all=true', follow_redirects=True)
    assert response.status_code in (200, 302)
    # No assertion needed for print, just ensure no error and jobs cleared
    from app.services import async_service
    assert async_service.processing_jobs == {}


def test_clear_session_clears_question_content(client):
    with client.session_transaction() as sess:
        sess['question_content'] = "What is the answer?"
        sess['question_id'] = 42  # To also test both are cleared
    response = client.get('/clear_session?clear_question=true', follow_redirects=True)
    assert response.status_code in (200, 302)
    with client.session_transaction() as sess:
        assert 'question_content' not in sess
        assert 'question_id' not in sess

