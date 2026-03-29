from http import client as http_client

import pytest
from django.urls import reverse

from ledger.models import Store
from tests import factories


class TestStoreViewSet:
    def test_requires_authentication(self, client):
        response = client.get(reverse("ledger:store-list"))

        assert response.status_code == http_client.UNAUTHORIZED
        assert response["content-type"] == "application/json"


@pytest.mark.xfail(reason="StoreViewSet uses non-existent `user` field in queryset/save", strict=False)
def test_store_authenticated_list_intended_behavior(client):
    user = factories.User(username="store_list_user", password="password123")
    client.authenticate_user(user.username, "password123")

    Store.objects.create(name="AH", created_by=user)

    response = client.get(reverse("ledger:store-list"))

    assert response.status_code == http_client.OK
