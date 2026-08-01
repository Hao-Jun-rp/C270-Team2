def test_reviews_page_loads(client):
    response = client.get("/reviews/", follow_redirects=True)
    assert response.status_code == 200


def test_reviews_page_contains_heading(client):
    response = client.get("/reviews/", follow_redirects=True)

    assert response.status_code == 200
    assert b"reviews" in response.data.lower()


def test_invalid_reviews_page_returns_not_found(client):
    response = client.get("/reviews/invalid-page")

    assert response.status_code == 404