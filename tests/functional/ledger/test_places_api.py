from http import client as http_client

from django.urls import reverse

from ledger.models import Place
from tests import factories


class TestPlaceViewSet:
    def _auth(self, client, username="place_user", password="password123"):
        user = factories.User(username=username, password=password)
        client.authenticate_user(username, password)
        return user

    def test_requires_authentication(self, client):
        response = client.get(reverse("ledger:place-list"))

        assert response.status_code == http_client.UNAUTHORIZED
        assert response["content-type"] == "application/json"

    def test_list_returns_only_current_users_places(self, client):
        user = self._auth(client)
        other = factories.User(username="place_other", password="password123")

        Place.objects.create(name="Amsterdam", created_by=user)
        Place.objects.create(name="Rotterdam", created_by=other)

        response = client.get(reverse("ledger:place-list"))

        assert response.status_code == http_client.OK
        assert [item["name"] for item in response.data["results"]] == ["Amsterdam"]

    def test_create_sets_created_by_to_authenticated_user(self, client):
        user = self._auth(client, username="place_create")

        response = client.post(
            reverse("ledger:place-list"),
            {"name": "Utrecht"},
            format="json",
        )

        assert response.status_code == http_client.CREATED
        created = Place.objects.get(pk=response.data["id"])
        assert created.created_by_id == user.id
        assert response.data["name"] == "Utrecht"

    def test_retrieve_returns_own_place(self, client):
        user = self._auth(client, username="place_retrieve")
        place = Place.objects.create(name="Leiden", created_by=user)

        response = client.get(reverse("ledger:place-detail", args=[place.id]))

        assert response.status_code == http_client.OK
        assert response.data["id"] == place.id
        assert response.data["name"] == "Leiden"

    def test_patch_updates_own_place(self, client):
        user = self._auth(client, username="place_patch")
        place = Place.objects.create(name="Old Place", created_by=user)

        response = client.patch(
            reverse("ledger:place-detail", args=[place.id]),
            {"name": "New Place"},
            format="json",
        )

        assert response.status_code == http_client.OK
        place.refresh_from_db()
        assert place.name == "New Place"
        assert place.updated_by_id == user.id

    def test_delete_soft_deletes_own_place(self, client):
        user = self._auth(client, username="place_delete")
        place = Place.objects.create(name="Delete Place", created_by=user)

        response = client.delete(reverse("ledger:place-detail", args=[place.id]))

        assert response.status_code == http_client.NO_CONTENT
        place.refresh_from_db()
        assert place.deleted_at is not None
        assert place.deleted_by_id == user.id

    def test_cannot_access_other_users_place(self, client):
        self._auth(client, username="place_owner")
        other = factories.User(username="place_other_owner", password="password123")
        other_place = Place.objects.create(name="Private Place", created_by=other)

        response = client.get(reverse("ledger:place-detail", args=[other_place.id]))

        assert response.status_code == http_client.NOT_FOUND
