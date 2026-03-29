from http import client as http_client

from django.urls import reverse

from tests import factories


class TestUserViewSet:
    def test_requires_authentication(self, client):
        response = client.get(reverse("ledger:user-list"))

        assert response.status_code == http_client.UNAUTHORIZED
        assert response["content-type"] == "application/json"

    def test_list_excludes_superusers(self, client):
        password = "password123"
        regular = factories.User(username="regular_user", password=password)
        superuser = factories.User(username="admin_user", password=password, is_superuser=True)

        client.authenticate_user(regular.username, password)

        response = client.get(reverse("ledger:user-list"))

        assert response.status_code == http_client.OK
        usernames = {item["username"] for item in response.data}
        assert regular.username in usernames
        assert superuser.username not in usernames
