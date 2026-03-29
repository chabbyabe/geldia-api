from datetime import datetime
from decimal import Decimal
from http import client as http_client

from django.urls import reverse
from django.utils import timezone

from ledger.constants import TxnType
from ledger.models import Transaction, TransactionType
from tests import factories
from users.models import Account


class TestTransactionViewSet:
    def _auth(self, client, username="txn_user", password="password123"):
        user = factories.User(username=username, password=password)
        client.authenticate_user(username, password)
        return user

    def _txn_type(self, name):
        return TransactionType.objects.create(name=name, color="#111111", icon="icon")

    def test_requires_authentication(self, client):
        response = client.get(reverse("ledger:transaction-list"))

        assert response.status_code == http_client.UNAUTHORIZED
        assert response["content-type"] == "application/json"

    def test_list_returns_only_current_user(self, client):
        user = self._auth(client)
        other = factories.User(username="txn_other", password="password123")

        income = self._txn_type(TxnType.INCOME)

        account = Account.objects.create(user=user, name="Main", balance=Decimal("0.00"))
        other_account = Account.objects.create(user=other, name="Other", balance=Decimal("0.00"))

        Transaction.all_objects.create(
            user=user,
            account=account,
            transaction_type=income,
            name="my txn",
            amount=Decimal("10.00"),
            transaction_at=timezone.make_aware(datetime(2026, 1, 1, 10, 0, 0)),
            created_by=user,
        )
        Transaction.all_objects.create(
            user=other,
            account=other_account,
            transaction_type=income,
            name="other txn",
            amount=Decimal("20.00"),
            transaction_at=timezone.make_aware(datetime(2026, 1, 2, 10, 0, 0)),
            created_by=other,
        )

        response = client.get(reverse("ledger:transaction-list"))

        assert response.status_code == http_client.OK
        names = {item["name"] for item in response.data["results"]}
        assert "my txn" in names
        assert "other txn" not in names

    def test_create_income_updates_account_balance(self, client):
        user = self._auth(client, username="txn_create_user")
        income = self._txn_type(TxnType.INCOME)
        account = Account.objects.create(user=user, name="Salary", balance=Decimal("100.00"))

        response = client.post(
            reverse("ledger:transaction-list"),
            {
                "user_id": user.id,
                "account_id": account.id,
                "account": account.id,
                "transaction_type_id": income.id,
                "name": "January Salary",
                "amount": "1000.00",
                "net_amount": "700.00",
                "transaction_at": "2026-01-15T12:00:00Z",
                "tags_names": [],
            },
            format="json",
        )

        assert response.status_code == http_client.CREATED
        account.refresh_from_db()
        assert account.balance == Decimal("800.00")
