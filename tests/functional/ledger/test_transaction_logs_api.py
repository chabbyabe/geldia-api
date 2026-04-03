import json
from datetime import datetime
from decimal import Decimal
from http import client as http_client

from django.urls import reverse
from django.utils import timezone

from ledger.constants import TxnType, UserAction
from ledger.models import Transaction, TransactionLog, TransactionType
from tests import factories
from users.models import Account


class TestTransactionLogViewSet:
    def _auth(self, client, username="txn_log_user", password="password123"):
        user = factories.User(username=username, password=password)
        client.authenticate_user(username, password)
        return user

    def _txn_type(self, name=TxnType.EXPENSES):
        return TransactionType.objects.create(name=name, color="#111111", icon="icon")

    def _account(self, user, name="Main", balance="0.00"):
        return Account.objects.create(user=user, name=name, balance=Decimal(balance))

    def _transaction(self, user, name="Transaction", amount="10.00", txn_type=None):
        account = self._account(user, name=f"{name} account", balance="500.00")
        transaction_type = txn_type or self._txn_type()
        return Transaction.all_objects.create(
            user=user,
            account=account,
            transaction_type=transaction_type,
            name=name,
            amount=Decimal(amount),
            transaction_at=timezone.make_aware(datetime(2026, 1, 10, 10, 0, 0)),
            created_by=user,
        )

    def _log(
        self,
        *,
        user,
        transaction,
        action=UserAction.CREATE,
        created_at=None,
        new_data=None,
        old_data=None,
    ):
        log = TransactionLog.objects.create(
            transaction=transaction,
            action=action,
            performed_by=user,
            new_data=new_data or {
                "id": transaction.id,
                "name": transaction.name,
                "amount": str(transaction.amount),
            },
            old_data=old_data,
        )

        if created_at is not None:
            TransactionLog.objects.filter(pk=log.pk).update(created_at=created_at)
            log.refresh_from_db()

        return log

    def test_requires_authentication(self, client):
        response = client.get(reverse("ledger:log-transaction-logs"))

        assert response.status_code == http_client.UNAUTHORIZED
        assert response["content-type"] == "application/json"

    def test_list_returns_only_current_user_logs(self, client):
        user = self._auth(client)
        other = factories.User(username="txn_log_other", password="password123")

        user_transaction = self._transaction(user, name="User log txn")
        other_transaction = self._transaction(other, name="Other log txn")

        self._log(
            user=user,
            transaction=user_transaction,
            new_data={"id": user_transaction.id, "name": "User log txn"},
        )
        self._log(
            user=other,
            transaction=other_transaction,
            new_data={"id": other_transaction.id, "name": "Other log txn"},
        )

        response = client.get(reverse("ledger:log-transaction-logs"))

        assert response.status_code == http_client.OK
        assert response.data["count"] == 1
        assert [item["new_data"]["name"] for item in response.data["results"]] == ["User log txn"]

    def test_list_is_ordered_by_newest_created_at_first(self, client):
        user = self._auth(client, username="txn_log_order_user")
        first_transaction = self._transaction(user, name="Older transaction")
        second_transaction = self._transaction(user, name="Newer transaction")

        self._log(
            user=user,
            transaction=first_transaction,
            created_at=timezone.make_aware(datetime(2026, 1, 5, 9, 0, 0)),
            new_data={"id": first_transaction.id, "name": "Older transaction"},
        )
        self._log(
            user=user,
            transaction=second_transaction,
            created_at=timezone.make_aware(datetime(2026, 1, 6, 9, 0, 0)),
            new_data={"id": second_transaction.id, "name": "Newer transaction"},
        )

        response = client.get(reverse("ledger:log-transaction-logs"))

        assert response.status_code == http_client.OK
        assert [item["new_data"]["name"] for item in response.data["results"]] == [
            "Newer transaction",
            "Older transaction",
        ]

    def test_search_filters_logs_by_new_data_fields(self, client):
        user = self._auth(client, username="txn_log_search_user")
        groceries = self._transaction(user, name="Groceries run")
        rent = self._transaction(user, name="Rent payment")

        self._log(
            user=user,
            transaction=groceries,
            new_data={"id": groceries.id, "name": "Groceries run", "notes": "Bought fruit"},
        )
        self._log(
            user=user,
            transaction=rent,
            new_data={"id": rent.id, "name": "Rent payment", "notes": "Monthly housing"},
        )

        response = client.get(
            reverse("ledger:log-transaction-logs"),
            {"search": "fruit"},
        )

        assert response.status_code == http_client.OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["new_data"]["name"] == "Groceries run"

    def test_filter_model_filters_json_fields(self, client):
        user = self._auth(client, username="txn_log_filter_user")
        small = self._transaction(user, name="Coffee", amount="4.50")
        large = self._transaction(user, name="Weekly groceries", amount="87.25")

        self._log(
            user=user,
            transaction=small,
            new_data={"id": small.id, "name": "Coffee", "amount": 4.5},
        )
        self._log(
            user=user,
            transaction=large,
            new_data={"id": large.id, "name": "Weekly groceries", "amount": 87.25},
        )

        response = client.get(
            reverse("ledger:log-transaction-logs"),
            {
                "filterModel": json.dumps(
                    {
                        "items": [
                            {"field": "new_data.amount", "operator": ">", "value": "10"}
                        ]
                    }
                )
            },
        )

        assert response.status_code == http_client.OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["new_data"]["name"] == "Weekly groceries"

    def test_date_filters_use_log_created_at(self, client):
        user = self._auth(client, username="txn_log_date_user")
        march_log_txn = self._transaction(user, name="March transaction")
        april_log_txn = self._transaction(user, name="April transaction")

        self._log(
            user=user,
            transaction=march_log_txn,
            created_at=timezone.make_aware(datetime(2026, 3, 28, 8, 0, 0)),
            new_data={"id": march_log_txn.id, "name": "March transaction"},
        )
        self._log(
            user=user,
            transaction=april_log_txn,
            created_at=timezone.make_aware(datetime(2026, 4, 2, 8, 0, 0)),
            new_data={"id": april_log_txn.id, "name": "April transaction"},
        )

        response = client.get(
            reverse("ledger:log-transaction-logs"),
            {
                "startDate": "2026-04-01",
                "endDate": "2026-04-03",
            },
        )

        assert response.status_code == http_client.OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["new_data"]["name"] == "April transaction"
