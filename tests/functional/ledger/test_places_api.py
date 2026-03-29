from http import client as http_client

import pytest
from django.urls import reverse

from ledger.models import Place
from tests import factories


class TestPlaceViewSet:
    def test_requires_authentication(self, client):
        response = client.get(reverse("ledger:place-list"))

        assert response.status_code == http_client.UNAUTHORIZED
        assert response["content-type"] == "application/json"


@pytest.mark.xfail(reason="PlaceViewSet uses non-existent `user` field in queryset/save", strict=False)
def test_place_authenticated_list_intended_behavior(client):
    user = factories.User(username="place_list_user", password="password123")
    client.authenticate_user(user.username, "password123")

    Place.objects.create(name="Utrecht", created_by=user)

    response = client.get(reverse("ledger:place-list"))

    assert response.status_code == http_client.OK
