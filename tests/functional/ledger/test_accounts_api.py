from decimal import Decimal
from http import client as http_client

from django.urls import reverse

from tests import factories
from users.models import Account


class TestAccountViewSet:
    def _auth(self, client, username="accounts_user", password="password123"):
        user = factories.User(username=username, password=password)
        client.authenticate_user(username, password)
        return user

    def test_requires_authentication(self, client):
        response = client.get(reverse("ledger:account-list"))

        assert response.status_code == http_client.UNAUTHORIZED
        assert response["content-type"] == "application/json"

    def test_list_returns_own_and_shared_accounts(self, client):
        user = self._auth(client)
        other = factories.User(username="accounts_other", password="password123")

        own = Account.objects.create(user=user, name="Own Account", balance=Decimal("100.00"))
        shared = Account.objects.create(user=other, name="Shared Account", balance=Decimal("50.00"))
        shared.shared_users.add(user)
        Account.objects.create(user=other, name="Private Account", balance=Decimal("999.00"))

        response = client.get(reverse("ledger:account-list"))

        assert response.status_code == http_client.OK
        names = {item["name"] for item in response.data["results"]}
        assert own.name in names
        assert shared.name in names
        assert "Private Account" not in names

    def test_create_succeeds(self, client):
        user = self._auth(client, username="create_account_user")

        response = client.post(
            reverse("ledger:account-list"),
            {
                "name": "Wallet",
                "balance": "120.50",
                "icon": "wallet",
                "color": "#123456",
                "is_default": False,
                "shared_user_ids": [],
            },
            format="json",
        )

        assert response.status_code == http_client.CREATED
        assert response.data["name"] == "Wallet"
        assert response.data["user"]["id"] == user.id
