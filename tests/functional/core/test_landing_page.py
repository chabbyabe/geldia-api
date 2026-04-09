from django.urls import reverse


def test_landing_page_renders_branded_homepage(client):
    response = client.get(reverse("landing"))

    assert response.status_code == 200
    assert b"Geldia API" in response.content
    assert b"Track money with clarity, not clutter." in response.content
