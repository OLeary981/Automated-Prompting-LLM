def test_custom_404_errorhandler(client):
    """Test that the custom 404 error handler renders the 404 template."""
    response = client.get('/this-page-does-not-exist')
    assert response.status_code == 404
    assert b"404" in response.data  # Assumes your 404.html contains "404"
    assert b"Freepik" in response.data  # Attribution text or other unique content

def test_explicit_404_route(client):
    """Test that the /404 route renders the 404 template with 404 status."""
    response = client.get('/404')
    assert response.status_code == 404
    assert b"404" in response.data
    assert b"Freepik" in response.data