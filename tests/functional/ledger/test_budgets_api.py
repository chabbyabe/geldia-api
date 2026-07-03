from decimal import Decimal
from http import client as http_client
from datetime import datetime

from django.urls import reverse
from django.utils import timezone

from ledger.constants import TxnType
from ledger.models import Budget, Category, Transaction, TransactionType
from tests import factories
from users.models import Account


class TestBudgetViewSet:
    def _auth(self, client, username="budget_user", password="password123"):
        user = factories.User(username=username, password=password)
        client.authenticate_user(username, password)
        return user

    def _txn_type(self, name):
        transaction_type, _ = TransactionType.objects.get_or_create(
            name=name,
            defaults={"color": "#111111", "icon": "icon"},
        )
        return transaction_type

    def _account(self, user, name="Main", balance="0.00"):
        return Account.objects.create(user=user, name=name, balance=Decimal(balance))

    def _category(self, user, transaction_type, name="Food"):
        return Category.objects.create(
            name=name,
            transaction_type=transaction_type,
            created_by=user,
        )

    def test_create_budget_recalculates_existing_expenses(self, client):
        user = self._auth(client)
        expense = self._txn_type(TxnType.EXPENSES)
        account = self._account(user, balance="500.00")
        category = self._category(user, expense)

        Transaction.objects.create(
            user=user,
            account=account,
            transaction_type=expense,
            category=category,
            name="Groceries",
            amount=Decimal("75.50"),
            transaction_at=timezone.make_aware(datetime(2026, 6, 4, 12, 0, 0)),
            created_by=user,
        )

        response = client.post(
            reverse("ledger:budget-list"),
            {
                "account_id": account.id,
                "category_id": category.id,
                "year": 2026,
                "month": 6,
                "amount": "300.00",
            },
            format="json",
        )

        assert response.status_code == http_client.CREATED
        assert Decimal(response.data["spent_amount"]) == Decimal("75.50")
        assert Decimal(response.data["remaining_amount"]) == Decimal("224.50")

    def test_list_returns_only_current_user_budgets(self, client):
        user = self._auth(client, username="budget_list_user")
        other = factories.User(username="budget_list_other", password="password123")
        user_account = self._account(user, name="User Budget")
        other_account = self._account(other, name="Other Budget")
        expense = self._txn_type(TxnType.EXPENSES)
        user_category = self._category(user, expense, name="User Food")
        other_category = self._category(other, expense, name="Other Food")

        Budget.objects.create(
            account=user_account,
            category=user_category,
            year=2026,
            month=6,
            amount=Decimal("100.00"),
            spent_amount=Decimal("10.00"),
            created_by=user,
        )
        Budget.objects.create(
            account=other_account,
            category=other_category,
            year=2026,
            month=6,
            amount=Decimal("200.00"),
            spent_amount=Decimal("20.00"),
            created_by=other,
        )

        response = client.get(reverse("ledger:budget-list"))

        assert response.status_code == http_client.OK
        assert len(response.data) == 1
        assert response.data[0]["account"]["id"] == user_account.id
        assert len(response.data[0]["categories"]) == 1
        assert response.data[0]["categories"][0]["amount"] == "100.00"

    def test_list_without_year_filter_defaults_to_current_year(self, client):
        user = self._auth(client, username="budget_current_year_user")
        expense = self._txn_type(TxnType.EXPENSES)
        account = self._account(user, name="Yearly Account")
        category = self._category(user, expense, name="Yearly Food")
        current_year = timezone.now().year

        Budget.objects.create(
            account=account,
            category=category,
            year=current_year - 1,
            month=12,
            amount=Decimal("180.00"),
            spent_amount=Decimal("15.00"),
            created_by=user,
        )
        newer_budget = Budget.objects.create(
            account=account,
            category=category,
            year=current_year,
            month=1,
            amount=Decimal("200.00"),
            spent_amount=Decimal("25.00"),
            created_by=user,
        )

        response = client.get(reverse("ledger:budget-list"))

        assert response.status_code == http_client.OK
        returned_budget_ids = {
            category["budget_id"]
            for item in response.data
            for category in item["categories"]
        }
        assert returned_budget_ids == {newer_budget.id}

    def test_list_filters_by_year_then_account_then_category(self, client):
        user = self._auth(client, username="budget_filter_user")
        expense = self._txn_type(TxnType.EXPENSES)
        account_a = self._account(user, name="A Account")
        account_b = self._account(user, name="B Account")
        category_a = self._category(user, expense, name="Alpha")
        category_b = self._category(user, expense, name="Beta")

        target_budget = Budget.objects.create(
            account=account_a,
            category=category_a,
            year=2026,
            month=6,
            amount=Decimal("100.00"),
            spent_amount=Decimal("10.00"),
            created_by=user,
        )
        Budget.objects.create(
            account=account_a,
            category=category_b,
            year=2026,
            month=6,
            amount=Decimal("120.00"),
            spent_amount=Decimal("20.00"),
            created_by=user,
        )
        Budget.objects.create(
            account=account_b,
            category=category_a,
            year=2026,
            month=6,
            amount=Decimal("140.00"),
            spent_amount=Decimal("30.00"),
            created_by=user,
        )
        Budget.objects.create(
            account=account_a,
            category=category_a,
            year=2025,
            month=6,
            amount=Decimal("160.00"),
            spent_amount=Decimal("40.00"),
            created_by=user,
        )

        response = client.get(
            reverse("ledger:budget-list"),
            {
                "year": 2026,
                "account_id": account_a.id,
                "category_id": category_a.id,
            },
        )

        assert response.status_code == http_client.OK
        assert len(response.data) == 1
        assert response.data[0]["categories"][0]["budget_id"] == (
            target_budget.id
        )

    def test_list_groups_categories_under_same_account_year_and_month(self, client):
        user = self._auth(client, username="budget_group_user")
        expense = self._txn_type(TxnType.EXPENSES)
        account = self._account(user, name="Grouped Account")
        groceries = self._category(user, expense, name="Groceries")
        transport = self._category(user, expense, name="Transport")

        groceries_budget = Budget.objects.create(
            account=account,
            category=groceries,
            year=2026,
            month=6,
            amount=Decimal("100.00"),
            spent_amount=Decimal("10.00"),
            created_by=user,
        )
        transport_budget = Budget.objects.create(
            account=account,
            category=transport,
            year=2026,
            month=6,
            amount=Decimal("80.00"),
            spent_amount=Decimal("20.00"),
            created_by=user,
        )

        response = client.get(reverse("ledger:budget-list"))

        assert response.status_code == http_client.OK
        assert len(response.data) == 1

        result = response.data[0]
        assert result["account"]["id"] == account.id
        assert result["year"] == 2026
        assert result["month"] == 6

        category_budget_ids = {item["budget_id"] for item in result["categories"]}
        assert category_budget_ids == {groceries_budget.id, transport_budget.id}

    def test_update_budget_month_recalculates_spent_amount(self, client):
        user = self._auth(client, username="budget_patch_user")
        expense = self._txn_type(TxnType.EXPENSES)
        account = self._account(user, balance="500.00")
        category = self._category(user, expense)

        Transaction.objects.create(
            user=user,
            account=account,
            transaction_type=expense,
            category=category,
            name="Rent",
            amount=Decimal("120.00"),
            transaction_at=timezone.make_aware(datetime(2026, 7, 1, 12, 0, 0)),
            created_by=user,
        )

        budget = Budget.objects.create(
            account=account,
            category=category,
            year=2026,
            month=6,
            amount=Decimal("500.00"),
            spent_amount=Decimal("0.00"),
            created_by=user,
        )

        response = client.patch(
            reverse("ledger:budget-detail", args=[budget.id]),
            {"month": 7},
            format="json",
        )

        assert response.status_code == http_client.OK
        assert Decimal(response.data["spent_amount"]) == Decimal("120.00")

    def test_create_full_year_budget_creates_twelve_records(self, client):
        user = self._auth(client, username="budget_year_user")
        expense = self._txn_type(TxnType.EXPENSES)
        account = self._account(user, balance="500.00")
        category = self._category(user, expense)

        Transaction.objects.create(
            user=user,
            account=account,
            transaction_type=expense,
            category=category,
            name="January bill",
            amount=Decimal("20.00"),
            transaction_at=timezone.make_aware(datetime(2026, 1, 10, 12, 0, 0)),
            created_by=user,
        )
        Transaction.objects.create(
            user=user,
            account=account,
            transaction_type=expense,
            category=category,
            name="June bill",
            amount=Decimal("45.00"),
            transaction_at=timezone.make_aware(datetime(2026, 6, 10, 12, 0, 0)),
            created_by=user,
        )

        response = client.post(
            reverse("ledger:budget-list"),
            {
                "account_id": account.id,
                "category_id": category.id,
                "year": 2026,
                "amount": "300.00",
                "create_full_year": True,
            },
            format="json",
        )

        assert response.status_code == http_client.CREATED
        assert isinstance(response.data, list)
        assert len(response.data) == 12
        assert Budget.objects.filter(
            account=account,
            category=category,
            year=2026,
        ).count() == 12
        january_budget = next(item for item in response.data if item["month"] == 1)
        june_budget = next(item for item in response.data if item["month"] == 6)
        assert Decimal(january_budget["spent_amount"]) == Decimal("20.00")
        assert Decimal(june_budget["spent_amount"]) == Decimal("45.00")

    def test_create_budget_without_month_defaults_to_full_year(self, client):
        user = self._auth(client, username="budget_year_default_user")
        expense = self._txn_type(TxnType.EXPENSES)
        account = self._account(user, balance="500.00")
        category = self._category(user, expense)

        response = client.post(
            reverse("ledger:budget-list"),
            {
                "account_id": account.id,
                "category_id": category.id,
                "year": 2026,
                "amount": "300.00",
            },
            format="json",
        )

        assert response.status_code == http_client.CREATED
        assert isinstance(response.data, list)
        assert len(response.data) == 12
        assert Budget.objects.filter(
            account=account,
            category=category,
            year=2026,
        ).count() == 12

    def test_create_full_year_budget_rejects_existing_months(self, client):
        user = self._auth(client, username="budget_year_duplicate_user")
        expense = self._txn_type(TxnType.EXPENSES)
        account = self._account(user, balance="500.00")
        category = self._category(user, expense)

        Budget.objects.create(
            account=account,
            category=category,
            year=2026,
            month=3,
            amount=Decimal("150.00"),
            spent_amount=Decimal("0.00"),
            created_by=user,
        )

        response = client.post(
            reverse("ledger:budget-list"),
            {
                "account_id": account.id,
                "category_id": category.id,
                "year": 2026,
                "amount": "300.00",
                "create_full_year": True,
            },
            format="json",
        )

        assert response.status_code == http_client.BAD_REQUEST
        assert "month(s): 3" in str(response.data)
        assert Budget.objects.filter(
            account=account,
            category=category,
            year=2026,
        ).count() == 1

    def test_delete_budget_soft_deletes_record(self, client):
        user = self._auth(client, username="budget_delete_user")
        expense = self._txn_type(TxnType.EXPENSES)
        account = self._account(user, balance="500.00")
        category = self._category(user, expense)
        budget = Budget.objects.create(
            account=account,
            category=category,
            year=2026,
            month=6,
            amount=Decimal("300.00"),
            spent_amount=Decimal("0.00"),
            created_by=user,
        )

        response = client.delete(reverse("ledger:budget-detail", args=[budget.id]))

        assert response.status_code == http_client.NO_CONTENT
        budget.refresh_from_db()
        assert budget.deleted_at is not None
        assert budget.deleted_by_id == user.id


class TestBudgetTransactionSync:
    def _auth(self, client, username="budget_txn_user", password="password123"):
        user = factories.User(username=username, password=password)
        client.authenticate_user(username, password)
        return user

    def _txn_type(self, name):
        transaction_type, _ = TransactionType.objects.get_or_create(
            name=name,
            defaults={"color": "#111111", "icon": "icon"},
        )
        return transaction_type

    def _account(self, user, name="Main", balance="0.00"):
        return Account.objects.create(user=user, name=name, balance=Decimal(balance))

    def _category(self, user, transaction_type, name="Food"):
        return Category.objects.create(
            name=name,
            transaction_type=transaction_type,
            created_by=user,
        )

    def test_create_expense_transaction_increases_budget_spent_amount(self, client):
        user = self._auth(client)
        expense = self._txn_type(TxnType.EXPENSES)
        account = self._account(user, balance="500.00")
        category = self._category(user, expense)
        budget = Budget.objects.create(
            account=account,
            category=category,
            year=2026,
            month=6,
            amount=Decimal("300.00"),
            spent_amount=Decimal("0.00"),
            created_by=user,
        )

        response = client.post(
            reverse("ledger:transaction-list"),
            {
                "user_id": user.id,
                "account_id": account.id,
                "transaction_type_id": expense.id,
                "name": "Groceries",
                "amount": "40.00",
                "category_name": category.name,
                "transaction_at": "2026-06-15T12:00:00Z",
                "tags_names": [],
            },
            format="json",
        )

        assert response.status_code == http_client.CREATED
        budget.refresh_from_db()
        assert budget.spent_amount == Decimal("40.00")

    def test_updating_expense_transaction_month_moves_budget_spend(self, client):
        user = self._auth(client, username="budget_txn_patch_user")
        expense = self._txn_type(TxnType.EXPENSES)
        account = self._account(user, balance="500.00")
        category = self._category(user, expense)
        june_budget = Budget.objects.create(
            account=account,
            category=category,
            year=2026,
            month=6,
            amount=Decimal("300.00"),
            spent_amount=Decimal("0.00"),
            created_by=user,
        )
        july_budget = Budget.objects.create(
            account=account,
            category=category,
            year=2026,
            month=7,
            amount=Decimal("300.00"),
            spent_amount=Decimal("0.00"),
            created_by=user,
        )

        transaction = Transaction.objects.create(
            user=user,
            account=account,
            transaction_type=expense,
            category=category,
            name="Fuel",
            amount=Decimal("25.00"),
            transaction_at=timezone.make_aware(datetime(2026, 6, 20, 12, 0, 0)),
            previous_balance=Decimal("500.00"),
            created_by=user,
        )
        june_budget.spent_amount = Decimal("25.00")
        june_budget.save(update_fields=["spent_amount", "updated_at"])

        response = client.patch(
            reverse("ledger:transaction-detail", args=[transaction.id]),
            {
                "transaction_at": "2026-07-20T12:00:00Z",
                "amount": "30.00",
            },
            format="json",
        )

        assert response.status_code == http_client.OK
        june_budget.refresh_from_db()
        july_budget.refresh_from_db()
        assert june_budget.spent_amount == Decimal("0.00")
        assert july_budget.spent_amount == Decimal("30.00")

    def test_deleting_expense_transaction_restores_budget_spent_amount(self, client):
        user = self._auth(client, username="budget_txn_delete_user")
        expense = self._txn_type(TxnType.EXPENSES)
        account = self._account(user, balance="500.00")
        category = self._category(user, expense)
        budget = Budget.objects.create(
            account=account,
            category=category,
            year=2026,
            month=6,
            amount=Decimal("300.00"),
            spent_amount=Decimal("60.00"),
            created_by=user,
        )
        transaction = Transaction.objects.create(
            user=user,
            account=account,
            transaction_type=expense,
            category=category,
            name="Dining",
            amount=Decimal("60.00"),
            transaction_at=timezone.make_aware(datetime(2026, 6, 22, 12, 0, 0)),
            previous_balance=Decimal("560.00"),
            created_by=user,
        )

        response = client.delete(reverse("ledger:transaction-detail", args=[transaction.id]))

        assert response.status_code == http_client.NO_CONTENT
        budget.refresh_from_db()
        assert budget.spent_amount == Decimal("0.00")

    def test_expense_with_other_category_does_not_change_budget(self, client):
        user = self._auth(client, username="budget_txn_other_category_user")
        expense = self._txn_type(TxnType.EXPENSES)
        account = self._account(user, balance="500.00")
        groceries = self._category(user, expense, name="Groceries")
        transport = self._category(user, expense, name="Transport")
        budget = Budget.objects.create(
            account=account,
            category=groceries,
            year=2026,
            month=6,
            amount=Decimal("300.00"),
            spent_amount=Decimal("0.00"),
            created_by=user,
        )

        response = client.post(
            reverse("ledger:transaction-list"),
            {
                "user_id": user.id,
                "account_id": account.id,
                "transaction_type_id": expense.id,
                "name": "Bus pass",
                "amount": "40.00",
                "category_name": transport.name,
                "transaction_at": "2026-06-15T12:00:00Z",
                "tags_names": [],
            },
            format="json",
        )

        assert response.status_code == http_client.CREATED
        budget.refresh_from_db()
        assert budget.spent_amount == Decimal("0.00")
