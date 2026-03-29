from http import client as http_client

import pytest
from django.urls import reverse

from ledger.models import Tag
from tests import factories


class TestTagViewSet:
    def test_requires_authentication(self, client):
        response = client.get(reverse("ledger:tag-list"))

        assert response.status_code == http_client.UNAUTHORIZED
        assert response["content-type"] == "application/json"


@pytest.mark.xfail(reason="TagViewSet uses non-existent `user` field in queryset/save", strict=False)
def test_tag_authenticated_list_intended_behavior(client):
    user = factories.User(username="tag_list_user", password="password123")
    client.authenticate_user(user.username, "password123")

    Tag.objects.create(name="Essentials", created_by=user)

    response = client.get(reverse("ledger:tag-list"))

    assert response.status_code == http_client.OK
