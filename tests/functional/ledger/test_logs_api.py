import json
from datetime import datetime
from decimal import Decimal
from http import client as http_client

from django.urls import reverse
from django.utils import timezone

from ledger.constants import TxnType, UserAction
from ledger.models import AccountLog, Transaction, TransactionLog, TransactionType
from tests import factories
from users.models import Account


class TestTransactionLogViewSet:
    def _auth(self, client, username="txn_log_user", password="password123"):
        user = factories.User(username=username, password=password)
        client.authenticate_user(username, password)
        return user

    def _txn_type(self, name=TxnType.EXPENSES):
        transaction_type, _ = TransactionType.objects.get_or_create(
            name=name,
            defaults={"color": "#111111", "icon": "icon"},
        )
        return transaction_type

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
        response = client.get(reverse("ledger:transaction-log-list"))

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

        response = client.get(reverse("ledger:transaction-log-list"))

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

        response = client.get(reverse("ledger:transaction-log-list"))

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
            reverse("ledger:transaction-log-list"),
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
            reverse("ledger:transaction-log-list"),
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
            reverse("ledger:transaction-log-list"),
            {
                "startDate": "2026-04-01",
                "endDate": "2026-04-03",
            },
        )

        assert response.status_code == http_client.OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["new_data"]["name"] == "April transaction"


class TestAccountLogViewSet:
    def _auth(self, client, username="account_log_user", password="password123"):
        user = factories.User(username=username, password=password)
        client.authenticate_user(username, password)
        return user

    def _account(self, user, name="Main", balance="0.00"):
        return Account.objects.create(user=user, name=name, balance=Decimal(balance))

    def _log(
        self,
        *,
        account,
        user,
        action=UserAction.CREATE,
        new_data=None,
        old_data=None,
        note=None,
    ):
        return AccountLog.objects.create(
            account=account,
            performed_by=user,
            action=action,
            old_data=old_data,
            new_data=new_data or {"id": account.id, "name": account.name},
            note=note,
        )

    def test_requires_authentication(self, client):
        response = client.get(reverse("ledger:account-log-list"))

        assert response.status_code == http_client.UNAUTHORIZED
        assert response["content-type"] == "application/json"

    def test_list_returns_only_visible_account_logs(self, client):
        user = self._auth(client)
        other = factories.User(username="account_log_other", password="password123")

        own_account = self._account(user, name="Own Account")
        shared_account = self._account(other, name="Shared Account")
        shared_account.shared_users.add(user)
        private_account = self._account(other, name="Private Account")

        self._log(account=own_account, user=user, new_data={"name": "Own Account"})
        self._log(account=shared_account, user=other, new_data={"name": "Shared Account"})
        self._log(account=private_account, user=other, new_data={"name": "Private Account"})

        response = client.get(reverse("ledger:account-log-list"))

        assert response.status_code == http_client.OK
        assert response.data["count"] == 2
        names = {item["new_data"]["name"] for item in response.data["results"]}
        assert names == {"Own Account", "Shared Account"}

    def test_create_succeeds_for_visible_account(self, client):
        user = self._auth(client, username="account_log_create_user")
        account = self._account(user, name="Travel Fund", balance="100.00")

        response = client.post(
            reverse("ledger:account-log-list"),
            {
                "account_id": account.id,
                "action": UserAction.UPDATE,
                "old_data": {"name": "Travel"},
                "new_data": {"name": "Travel Fund"},
                "note": "Renamed account",
            },
            format="json",
        )

        assert response.status_code == http_client.CREATED
        assert response.data["action"] == UserAction.UPDATE
        assert response.data["performed_by"]["id"] == user.id
        assert response.data["account"]["id"] == account.id

    def test_create_rejects_inaccessible_account(self, client):
        user = self._auth(client, username="account_log_forbidden_user")
        other = factories.User(username="account_log_owner", password="password123")
        account = self._account(other, name="Private Account")

        response = client.post(
            reverse("ledger:account-log-list"),
            {
                "account_id": account.id,
                "action": UserAction.CREATE,
                "new_data": {"name": "Private Account"},
            },
            format="json",
        )

        assert response.status_code == http_client.BAD_REQUEST
        assert response.data["account_id"] == ["You do not have access to this account."]

    def test_patch_updates_owned_log(self, client):
        user = self._auth(client, username="account_log_patch_user")
        account = self._account(user, name="Wallet")
        log = self._log(account=account, user=user, note="Initial note")

        response = client.patch(
            reverse("ledger:account-log-detail", args=[log.id]),
            {"note": "Updated note"},
            format="json",
        )

        assert response.status_code == http_client.OK
        assert response.data["note"] == "Updated note"

    def test_delete_removes_owned_log(self, client):
        user = self._auth(client, username="account_log_delete_user")
        account = self._account(user, name="Wallet")
        log = self._log(account=account, user=user)

        response = client.delete(reverse("ledger:account-log-detail", args=[log.id]))

        assert response.status_code == http_client.NO_CONTENT
        assert not AccountLog.objects.filter(pk=log.pk).exists()

    def test_filter_model_filters_json_fields(self, client):
        user = self._auth(client, username="account_log_filter_user")
        small = self._account(user, name="Cash", balance="10.00")
        large = self._account(user, name="Savings", balance="500.00")

        self._log(account=small, user=user, new_data={"name": "Cash", "balance": 10})
        self._log(account=large, user=user, new_data={"name": "Savings", "balance": 500})

        response = client.get(
            reverse("ledger:account-log-list"),
            {
                "filterModel": json.dumps(
                    {
                        "items": [
                            {"field": "new_data.balance", "operator": ">", "value": "100"}
                        ]
                    }
                )
            },
        )

        assert response.status_code == http_client.OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["new_data"]["name"] == "Savings"

    def test_account_crud_creates_audit_logs(self, client):
        self._auth(client, username="account_log_audit_user")

        create_response = client.post(
            reverse("ledger:account-list"),
            {
                "name": "Emergency Fund",
                "balance": "250.00",
                "icon": "shield",
                "color": "#224466",
            },
            format="json",
        )

        assert create_response.status_code == http_client.CREATED
        account_id = create_response.data["id"]

        create_log = AccountLog.objects.get(account_id=account_id, action=UserAction.CREATE)
        assert create_log.new_data["name"] == "Emergency Fund"

        update_response = client.patch(
            reverse("ledger:account-detail", args=[account_id]),
            {"name": "Emergency Savings"},
            format="json",
        )

        assert update_response.status_code == http_client.OK

        update_log = (
            AccountLog.objects.filter(account_id=account_id, action=UserAction.UPDATE)
            .order_by("-created_at")
            .first()
        )
        assert update_log is not None
        assert update_log.old_data["name"] == "Emergency Fund"
        assert update_log.new_data["name"] == "Emergency Savings"

        delete_response = client.delete(reverse("ledger:account-detail", args=[account_id]))

        assert delete_response.status_code == http_client.NO_CONTENT

        delete_log = (
            AccountLog.objects.filter(account_id=account_id, action=UserAction.DELETE)
            .order_by("-created_at")
            .first()
        )
        assert delete_log is not None
        assert delete_log.old_data["name"] == "Emergency Savings"

        account = Account.all_objects.get(pk=account_id)
        assert account.deleted_at is not None
