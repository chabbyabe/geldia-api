from http import client as http_client

from django.urls import reverse

from tests import factories
from users.models import Company


class TestCompanyViewSet:
    def _auth(self, client, username="company_user", password="password123"):
        user = factories.User(username=username, password=password)
        client.authenticate_user(username, password)
        return user

    def test_requires_authentication(self, client):
        response = client.get(reverse("company-list"))

        assert response.status_code == http_client.UNAUTHORIZED
        assert response["content-type"] == "application/json"

    def test_list_returns_only_current_user_companies(self, client):
        user = self._auth(client, username="company_list")
        other = factories.User(username="company_other", password="password123")

        own_company = Company.objects.create(name="Acme", created_by=user)
        Company.objects.create(name="Other Co", created_by=other)

        response = client.get(reverse("company-list"))

        assert response.status_code == http_client.OK
        assert [item["id"] for item in response.data] == [own_company.id]

    def test_create_sets_created_by_to_authenticated_user(self, client):
        user = self._auth(client, username="company_create")

        response = client.post(
            reverse("company-list"),
            {"name": "Travel Corp"},
            format="json",
        )

        assert response.status_code == http_client.CREATED
        company = Company.objects.get(pk=response.data["id"])
        assert company.created_by_id == user.id
        assert response.data["name"] == "Travel Corp"

    def test_create_returns_error_when_company_name_already_exists_for_user(self, client):
        user = self._auth(client, username="company_duplicate")
        Company.objects.create(name="Acme", created_by=user)

        response = client.post(
            reverse("company-list"),
            {"name": "acme"},
            format="json",
        )

        assert response.status_code == http_client.BAD_REQUEST
        assert response.data["non_field_errors"] == ["Company already exists."]

    def test_retrieve_returns_own_company(self, client):
        user = self._auth(client, username="company_retrieve")
        company = Company.objects.create(name="Own Co", created_by=user)

        response = client.get(reverse("company-detail", args=[company.id]))

        assert response.status_code == http_client.OK
        assert response.data["id"] == company.id
        assert response.data["name"] == "Own Co"

    def test_retrieve_other_users_company_returns_404(self, client):
        self._auth(client, username="company_retrieve_blocked")
        other = factories.User(username="company_other_retrieve", password="password123")
        company = Company.objects.create(name="Hidden Co", created_by=other)

        response = client.get(reverse("company-detail", args=[company.id]))

        assert response.status_code == http_client.NOT_FOUND

    def test_patch_updates_own_company(self, client):
        user = self._auth(client, username="company_patch")
        company = Company.objects.create(name="Old Co", created_by=user)

        response = client.patch(
            reverse("company-detail", args=[company.id]),
            {"name": "Updated Co"},
            format="json",
        )

        assert response.status_code == http_client.OK
        company.refresh_from_db()
        assert company.name == "Updated Co"
        assert company.updated_by_id == user.id

    def test_delete_soft_deletes_own_company(self, client):
        user = self._auth(client, username="company_delete")
        company = Company.objects.create(name="Disposable Co", created_by=user)

        response = client.delete(reverse("company-detail", args=[company.id]))

        assert response.status_code == http_client.NO_CONTENT
        company.refresh_from_db()
        assert company.deleted_at is not None
        assert company.deleted_by_id == user.id
