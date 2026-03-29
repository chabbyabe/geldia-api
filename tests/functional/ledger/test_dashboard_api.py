from datetime import datetime
from decimal import Decimal
from http import client as http_client

from django.urls import reverse
from django.utils import timezone

from ledger.constants import DateRange, TxnType
from ledger.models import Category, Transaction, TransactionType
from tests import factories
from users.models import Account


class TestDashboardViewSet:

    def _get_current_year(self):
        return timezone.now().year
    
    def _create_user_and_authenticate(self, client, username="ledger:dashboard_user", password="password123"):
        user = factories.User(username=username, password=password)
        client.authenticate_user(username, password)
        return user

    def _create_account(self, user, name="Main", balance="0"):
        return Account.objects.create(
            user=user,
            name=name,
            balance=Decimal(balance),
        )

    def _create_transaction_type(self, name, color="#111111", icon="icon"):
        return TransactionType.objects.create(name=name, color=color, icon=icon)

    def _create_category(self, name, transaction_type, parent=None, color="#222222", icon="tag"):
        return Category.objects.create(
            name=name,
            transaction_type=transaction_type,
            parent_category=parent,
            color=color,
            icon=icon,
        )

    def _create_transaction(
        self,
        *,
        user,
        account,
        transaction_type,
        amount,
        transaction_at,
        name="txn",
        category=None,
        net_amount=None,
        gross_amount=None,
        created_by=None,
        deleted_at=None,
    ):
        return Transaction.all_objects.create(
            user=user,
            account=account,
            transaction_type=transaction_type,
            amount=Decimal(amount),
            net_amount=Decimal(net_amount) if net_amount is not None else None,
            gross_amount=Decimal(gross_amount) if gross_amount is not None else None,
            name=name,
            transaction_at=transaction_at,
            category=category,
            created_by=created_by or user,
            deleted_at=deleted_at,
        )

    def test_recent_transactions_requires_authentication(self, client):
        response = client.get(reverse("ledger:dashboard-recent-transactions"))

        assert response.status_code == http_client.UNAUTHORIZED
        assert response["content-type"] == "application/json"

    def test_recent_transactions_returns_latest_five(self, client):
        user = self._create_user_and_authenticate(client)
        income = self._create_transaction_type(TxnType.INCOME)
        account = self._create_account(user)

        tx_ids = []
        for i in range(6):
            tx = self._create_transaction(
                user=user,
                account=account,
                transaction_type=income,
                amount=str(100 + i),
                transaction_at=timezone.now(),
                name=f"tx-{i}",
            )
            tx_ids.append(tx.id)

        base = timezone.now()
        for idx, tx_id in enumerate(tx_ids):
            Transaction.all_objects.filter(id=tx_id).update(created_at=base + timezone.timedelta(minutes=idx))

        response = client.get(reverse("ledger:dashboard-recent-transactions"))

        assert response.status_code == http_client.OK
        assert len(response.data) == 5
        assert response.data[0]["name"] == "tx-5"
        assert response.data[-1]["name"] == "tx-1"

    def test_category_overview_groups_by_category_and_date_range(self, client):
        user = self._create_user_and_authenticate(client, username="cat_user")
        other_user = factories.User(username="other_user", password="password123")

        expense = self._create_transaction_type(TxnType.EXPENSES)
        account = self._create_account(user)
        other_account = self._create_account(other_user)

        parent = self._create_category("Food", expense, color="#F00", icon="food")
        child = self._create_category("Groceries", expense, parent=parent, color="#0F0", icon="cart")

        current_year = self._get_current_year()
        
        march_1 = timezone.make_aware(datetime(current_year, 3, 1, 12, 0, 0))
        march_10 = timezone.make_aware(datetime(current_year, 3, 10, 12, 0, 0))
        april_1 = timezone.make_aware(datetime(current_year, 4, 1, 12, 0, 0))

        self._create_transaction(
            user=user,
            account=account,
            transaction_type=expense,
            amount="50.00",
            transaction_at=march_1,
            category=parent,
            created_by=user,
        )
        self._create_transaction(
            user=user,
            account=account,
            transaction_type=expense,
            amount="20.00",
            transaction_at=march_10,
            category=child,
            created_by=user,
        )
        self._create_transaction(
            user=user,
            account=account,
            transaction_type=expense,
            amount="999.00",
            transaction_at=april_1,
            category=parent,
            created_by=user,
        )
        self._create_transaction(
            user=other_user,
            account=other_account,
            transaction_type=expense,
            amount="777.00",
            transaction_at=march_10,
            category=parent,
            created_by=other_user,
        )

        response = client.get(
            reverse("ledger:dashboard-category-overview"),
            {
                "filterBy": DateRange.CUSTOM,
                "startDate": f"{current_year}-03-01",
                "endDate": f"{current_year}-03-31",
            },
        )

        assert response.status_code == http_client.OK
        assert len(response.data) == 2

        amounts = {item["name"]: item["amount"] for item in response.data}
        parents = {item["name"]: item["is_parent"] for item in response.data}

        assert amounts["Food"] == 50.0
        assert amounts["Groceries"] == 20.0
        assert parents["Food"] is False
        assert parents["Groceries"] is True

    def test_category_overview_requires_authentication(self, client):
        response = client.get(reverse("ledger:dashboard-category-overview"))

        assert response.status_code == http_client.UNAUTHORIZED
        assert response["content-type"] == "application/json"

    def test_category_overview_invalid_custom_dates_falls_back_to_unfiltered(self, client):
        user = self._create_user_and_authenticate(client, username="cat_invalid_date")
        expense = self._create_transaction_type(TxnType.EXPENSES)
        account = self._create_account(user)
        category = self._create_category("Utilities", expense, color="#00F", icon="bolt")
        current_year = self._get_current_year()

        self._create_transaction(
            user=user,
            account=account,
            transaction_type=expense,
            amount="80.00",
            transaction_at=timezone.make_aware(datetime(current_year, 1, 10, 12, 0, 0)),
            category=category,
            created_by=user,
        )
        self._create_transaction(
            user=user,
            account=account,
            transaction_type=expense,
            amount="20.00",
            transaction_at=timezone.make_aware(datetime(current_year, 2, 10, 12, 0, 0)),
            category=category,
            created_by=user,
        )

        response = client.get(
            reverse("ledger:dashboard-category-overview"),
            {
                "filterBy": DateRange.CUSTOM,
                "startDate": "invalid-date",
                "endDate": "also-invalid",
            },
        )
        assert response.status_code == http_client.OK
        assert len(response.data) == 0

    def test_summary_overview_returns_income_expenses_and_savings(self, client):
        user = self._create_user_and_authenticate(client, username="summary_user")

        income = self._create_transaction_type(TxnType.INCOME, color="#0A0", icon="income")
        expenses = self._create_transaction_type(TxnType.EXPENSES, color="#A00", icon="expense")

        main_account = self._create_account(user, name="Main")
        self._create_account(user, name="Savings", balance="1234.56")

        current_year = self._get_current_year()
        in_range_date = timezone.make_aware(datetime(current_year, 6, 1, 12, 0, 0))
        self._create_transaction(
            user=user,
            account=main_account,
            transaction_type=income,
            amount="4000.00",
            net_amount="3000.00",
            transaction_at=in_range_date,
        )
        self._create_transaction(
            user=user,
            account=main_account,
            transaction_type=expenses,
            amount="500.00",
            transaction_at=in_range_date,
        )

        response = client.get(reverse("ledger:dashboard-summary-overview"))

        assert response.status_code == http_client.OK
        assert len(response.data) == 3

        by_name = {item["name"]: item for item in response.data}
        assert by_name[TxnType.INCOME]["amount"] == "3000.00"
        assert by_name[TxnType.EXPENSES]["amount"] == "500.00"
        assert by_name["Savings"]["amount"] == "1234.56"
        assert by_name[TxnType.INCOME]["formatted_amount"] == "€3,000.00"
        assert by_name[TxnType.EXPENSES]["formatted_amount"] == "€500.00"

    def test_summary_overview_requires_authentication(self, client):
        response = client.get(reverse("ledger:dashboard-summary-overview"))

        assert response.status_code == http_client.UNAUTHORIZED
        assert response["content-type"] == "application/json"

    def test_year_overview_returns_monthly_income_and_expenses(self, client):
        user = self._create_user_and_authenticate(client, username="year_user")
        income = self._create_transaction_type(TxnType.INCOME)
        expenses = self._create_transaction_type(TxnType.EXPENSES)
        account = self._create_account(user)

        current_year = self._get_current_year()

        self._create_transaction(
            user=user,
            account=account,
            transaction_type=income,
            amount="0.00",
            gross_amount="5000.00",
            net_amount="4500.00",
            transaction_at=timezone.make_aware(datetime(current_year, 1, 15, 10, 0, 0)),
        )
        self._create_transaction(
            user=user,
            account=account,
            transaction_type=expenses,
            amount="1200.00",
            transaction_at=timezone.make_aware(datetime(current_year, 2, 10, 10, 0, 0)),
        )
        self._create_transaction(
            user=user,
            account=account,
            transaction_type=income,
            amount="0.00",
            net_amount="9999.00",
            transaction_at=timezone.make_aware(datetime(current_year, 1, 10, 10, 0, 0)),
        )

        response = client.get(reverse("ledger:dashboard-year-overview"), {"year": current_year})

        assert response.status_code == http_client.OK
        assert len(response.data) == 3

        data = response.data
        net_income_data = data[0]
        gross_income_data = data[1]
        expenses_data = data[2]
        assert net_income_data['data'][0] == 4500.00
        assert gross_income_data['data'][0] == 5000.00
        assert expenses_data['data'][1] == 1200.0
        assert net_income_data["year"] == str(current_year)
        assert expenses_data["year"] == str(current_year)

    def test_year_overview_requires_authentication(self, client):
        response = client.get(reverse("ledger:dashboard-year-overview"))

        assert response.status_code == http_client.UNAUTHORIZED
        assert response["content-type"] == "application/json"

    def test_year_overview_empty_data_returns_zeroed_series(self, client):
        self._create_user_and_authenticate(client, username="year_empty")
        
        current_year = self._get_current_year()
        response = client.get(reverse("ledger:dashboard-year-overview"), {})

        assert response.status_code == http_client.OK
        assert len(response.data) == 3
        
        by_name = {item["name"]: item for item in response.data}
        assert by_name[TxnType.INCOME]["data"] == [0] * 12
        assert by_name[TxnType.EXPENSES]["data"] == [0] * 12
        assert len(by_name[TxnType.INCOME]["label"]) == 12
        assert by_name[TxnType.INCOME]["year"] == str(current_year)
