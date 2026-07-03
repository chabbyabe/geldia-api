from __future__ import annotations

from decimal import Decimal

from django.db.models import Sum

from ledger.constants import TxnType
from ledger.models import Budget, Transaction


def get_budget_scope(transaction: Transaction) -> tuple[int, int, int, int]:
    if (
        transaction.transaction_type_id is None
        or transaction.transaction_at is None
        or transaction.account_id is None
        or transaction.category_id is None
        or transaction.transaction_type.name != TxnType.EXPENSES
    ):
        return None

    return (
        transaction.account_id,
        transaction.category_id,
        transaction.transaction_at.year,
        transaction.transaction_at.month,
    )


def calculate_spent_amount(
    *,
    account_id: int,
    category_id: int,
    year: int,
    month: int,
) -> Decimal:
    total = (
        Transaction.objects.filter(
            account_id=account_id,
            category_id=category_id,
            transaction_type__name=TxnType.EXPENSES,
            transaction_at__year=year,
            transaction_at__month=month,
        ).aggregate(total=Sum("amount")).get("total")
    )
    return total or Decimal("0.00")


def recalculate_budget_spent(budget: Budget) -> Budget:
    budget.spent_amount = calculate_spent_amount(
        account_id=budget.account_id,
        category_id=budget.category_id,
        year=budget.year,
        month=budget.month,
    )
    budget.save(update_fields=["spent_amount", "updated_at"])
    return budget


def apply_budget_delta(
    *,
    account_id: int,
    category_id: int,
    year: int,
    month: int,
    delta: Decimal,
) -> None:
    if delta == 0:
        return

    budget = (
        Budget.objects.select_for_update()
        .filter(
            account_id=account_id,
            category_id=category_id,
            year=year,
            month=month,
        )
        .first()
    )
    if budget is None:
        return

    budget.spent_amount += delta
    budget.save(update_fields=["spent_amount", "updated_at"])
