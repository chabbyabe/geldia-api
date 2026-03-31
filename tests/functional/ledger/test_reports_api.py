from datetime import date
from decimal import Decimal
from http import client as http_client

from django.urls import reverse

from ledger.constants import TxnType
from ledger.models import Store, Transaction, TransactionType
from tests import factories
from users.models import Account


class TestReportViewSet:
    def _auth(self, client, username="report_user", password="password123"):
        user = factories.User(username=username, password=password)
        client.authenticate_user(username, password)
        return user

    def _txn_type(self, name):
        return TransactionType.objects.create(name=name, color="#111111", icon="icon")

    def _account(self, user, name="Main", balance="0.00"):
        return Account.objects.create(user=user, name=name, balance=Decimal(balance))

    def _store(self, name, created_by):
        return Store.objects.create(name=name, created_by=created_by)

    def _income_transaction(
        self,
        *,
        user,
        account,
        transaction_type,
        debit_month_year,
        gross_amount,
        net_amount,
        store=None,
        created_by=None,
    ):
        return Transaction.all_objects.create(
            user=user,
            account=account,
            transaction_type=transaction_type,
            name=f"income-{debit_month_year.isoformat()}",
            amount=Decimal(net_amount),
            gross_amount=Decimal(gross_amount),
            net_amount=Decimal(net_amount),
            debit_month_year=debit_month_year,
            store=store,
            created_by=created_by or user,
        )

    def test_income_report_requires_authentication(self, client):
        response = client.get(reverse("ledger:report-income-report"))

        assert response.status_code == http_client.UNAUTHORIZED
        assert response["content-type"] == "application/json"

    def test_income_report_returns_monthly_aggregates_for_selected_year(self, client):
        user = self._auth(client)
        other_user = factories.User(username="report_other_user", password="password123")

        income = self._txn_type(TxnType.INCOME)
        expenses = self._txn_type(TxnType.EXPENSES)

        account = self._account(user)
        other_account = self._account(other_user, name="Other")

        acme = self._store("Acme BV", created_by=user)
        beta = self._store("Beta BV", created_by=user)
        other_store = self._store("Other Co", created_by=other_user)

        self._income_transaction(
            user=user,
            account=account,
            transaction_type=income,
            debit_month_year=date(2026, 1, 1),
            gross_amount="2000.00",
            net_amount="1500.00",
            store=acme,
        )
        self._income_transaction(
            user=user,
            account=account,
            transaction_type=income,
            debit_month_year=date(2026, 1, 1),
            gross_amount="1000.00",
            net_amount="700.00",
            store=beta,
        )
        self._income_transaction(
            user=user,
            account=account,
            transaction_type=income,
            debit_month_year=date(2026, 2, 1),
            gross_amount="500.00",
            net_amount="400.00",
            store=None,
        )
        self._income_transaction(
            user=user,
            account=account,
            transaction_type=income,
            debit_month_year=date(2025, 1, 1),
            gross_amount="999.00",
            net_amount="888.00",
            store=acme,
        )

        Transaction.all_objects.create(
            user=user,
            account=account,
            transaction_type=expenses,
            name="expense",
            amount=Decimal("99.00"),
            debit_month_year=date(2026, 1, 1),
            created_by=user,
        )
        self._income_transaction(
            user=other_user,
            account=other_account,
            transaction_type=income,
            debit_month_year=date(2026, 1, 1),
            gross_amount="3000.00",
            net_amount="2500.00",
            store=other_store,
            created_by=other_user,
        )

        response = client.get(
            reverse("ledger:report-income-report"),
            {"selectedYear": 2026, "compareYear": 2025},
        )

        assert response.status_code == http_client.OK
        assert response.data["selected_year"] == 2026
        assert response.data["compare_year"] == 2025
        assert len(response.data["base_data"]) == 12
        assert len(response.data["compare_data"]) == 12

        january = response.data["base_data"][0]
        february = response.data["base_data"][1]
        march = response.data["base_data"][2]
        compared_january = response.data["compare_data"][0]

        assert january["month"] == 1
        assert january["month_label"] == "Jan"
        assert january["gross_amount"] == 3000.0
        assert january["net_amount"] == 2200.0
        assert january["companies"] == [
            {"name": "Acme BV", "gross_amount": 2000.0, "net_amount": 1500.0},
            {"name": "Beta BV", "gross_amount": 1000.0, "net_amount": 700.0},
        ]

        assert february["month"] == 2
        assert february["month_label"] == "Feb"
        assert february["gross_amount"] == 500.0
        assert february["net_amount"] == 400.0
        assert february["companies"] == [
            {"name": "-", "gross_amount": 500.0, "net_amount": 400.0},
        ]

        assert march["month"] == 3
        assert march["gross_amount"] == 0
        assert march["net_amount"] == 0
        assert march["companies"] == []

        assert compared_january["month"] == 1
        assert compared_january["gross_amount"] == 999.0
        assert compared_january["net_amount"] == 888.0
        assert compared_january["companies"] == [
            {"name": "Acme BV", "gross_amount": 999.0, "net_amount": 888.0},
        ]

    def test_income_report_rejects_same_selected_and_compare_year(self, client):
        self._auth(client, username="report_validation_user")

        response = client.get(
            reverse("ledger:report-income-report"),
            {"selectedYear": 2026, "compareYear": 2026},
        )

        assert response.status_code == http_client.BAD_REQUEST
        assert response.data == {
            "compareYear": ["Cannot be the same as selectedYear."]
        }
