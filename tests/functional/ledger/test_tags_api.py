from http import client as http_client

from django.urls import reverse

from ledger.models import Tag
from tests import factories


class TestTagViewSet:
    def _auth(self, client, username="tag_user", password="password123"):
        user = factories.User(username=username, password=password)
        client.authenticate_user(username, password)
        return user

    def test_requires_authentication(self, client):
        response = client.get(reverse("ledger:tag-list"))

        assert response.status_code == http_client.UNAUTHORIZED
        assert response["content-type"] == "application/json"

    def test_list_returns_only_current_users_tags(self, client):
        user = self._auth(client)
        other = factories.User(username="tag_other", password="password123")

        Tag.objects.create(name="Essentials", color="#111111", created_by=user)
        Tag.objects.create(name="Hidden", color="#222222", created_by=other)

        response = client.get(reverse("ledger:tag-list"))

        assert response.status_code == http_client.OK
        assert [item["name"] for item in response.data["results"]] == ["Essentials"]

    def test_create_sets_created_by_to_authenticated_user(self, client):
        user = self._auth(client, username="tag_create")

        response = client.post(
            reverse("ledger:tag-list"),
            {"name": "Travel", "color": "#abcdef"},
            format="json",
        )

        assert response.status_code == http_client.CREATED
        created = Tag.objects.get(pk=response.data["id"])
        assert created.created_by_id == user.id
        assert response.data["name"] == "Travel"

    def test_create_returns_error_when_tag_name_already_exists(self, client):
        user = self._auth(client, username="tag_duplicate")
        Tag.objects.create(name="Travel", color="#111111", created_by=user)

        response = client.post(
            reverse("ledger:tag-list"),
            {"name": "travel", "color": "#abcdef"},
            format="json",
        )

        assert response.status_code == http_client.BAD_REQUEST
        assert response.data["name"] == ["Tag already exists."]

    def test_retrieve_returns_own_tag(self, client):
        user = self._auth(client, username="tag_retrieve")
        tag = Tag.objects.create(name="Groceries", color="#123456", created_by=user)

        response = client.get(reverse("ledger:tag-detail", args=[tag.id]))

        assert response.status_code == http_client.OK
        assert response.data["id"] == tag.id
        assert response.data["name"] == "Groceries"

    def test_patch_updates_own_tag(self, client):
        user = self._auth(client, username="tag_patch")
        tag = Tag.objects.create(name="Old", color="#000000", created_by=user)

        response = client.patch(
            reverse("ledger:tag-detail", args=[tag.id]),
            {"name": "Updated"},
            format="json",
        )

        assert response.status_code == http_client.OK
        tag.refresh_from_db()
        assert tag.name == "Updated"
        assert tag.updated_by_id == user.id

    def test_delete_soft_deletes_own_tag(self, client):
        user = self._auth(client, username="tag_delete")
        tag = Tag.objects.create(name="Disposable", color="#000000", created_by=user)

        response = client.delete(reverse("ledger:tag-detail", args=[tag.id]))

        assert response.status_code == http_client.NO_CONTENT
        tag.refresh_from_db()
        assert tag.deleted_at is not None
        assert tag.deleted_by_id == user.id

    def test_cannot_access_other_users_tag(self, client):
        self._auth(client, username="tag_owner")
        other = factories.User(username="tag_other_owner", password="password123")
        other_tag = Tag.objects.create(name="Private", color="#010101", created_by=other)

        response = client.get(reverse("ledger:tag-detail", args=[other_tag.id]))

        assert response.status_code == http_client.NOT_FOUND
