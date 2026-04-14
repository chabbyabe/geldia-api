from http import client as http_client

from django.urls import reverse

from ledger.models import Store
from tests import factories


class TestStoreViewSet:
    def _auth(self, client, username="store_user", password="password123"):
        user = factories.User(username=username, password=password)
        client.authenticate_user(username, password)
        return user

    def test_requires_authentication(self, client):
        response = client.get(reverse("ledger:store-list"))

        assert response.status_code == http_client.UNAUTHORIZED
        assert response["content-type"] == "application/json"

    def test_create_sets_created_by_to_authenticated_user(self, client):
        user = self._auth(client, username="store_create")

        response = client.post(
            reverse("ledger:store-list"),
            {"name": "Jumbo"},
            format="json",
        )

        assert response.status_code == http_client.CREATED
        created = Store.objects.get(pk=response.data["id"])
        assert created.created_by_id == user.id
        assert response.data["name"] == "Jumbo"

    def test_retrieve_returns_own_store(self, client):
        user = self._auth(client, username="store_retrieve")
        store = Store.objects.create(name="Kiosk", created_by=user)

        response = client.get(reverse("ledger:store-detail", args=[store.id]))

        assert response.status_code == http_client.OK
        assert response.data["id"] == store.id
        assert response.data["name"] == "Kiosk"

    def test_patch_updates_own_store(self, client):
        user = self._auth(client, username="store_patch")
        store = Store.objects.create(name="Old Store", created_by=user)

        response = client.patch(
            reverse("ledger:store-detail", args=[store.id]),
            {"name": "New Store"},
            format="json",
        )

        assert response.status_code == http_client.OK
        store.refresh_from_db()
        assert store.name == "New Store"
        assert store.updated_by_id == user.id

    def test_delete_soft_deletes_own_store(self, client):
        user = self._auth(client, username="store_delete")
        store = Store.objects.create(name="Delete Store", created_by=user)

        response = client.delete(reverse("ledger:store-detail", args=[store.id]))

        assert response.status_code == http_client.NO_CONTENT
        store.refresh_from_db()
        assert store.deleted_at is not None
        assert store.deleted_by_id == user.id
