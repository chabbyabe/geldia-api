import factory

from ledger.models import TransactionType as TransactionTypeModel

from tests.factories.users.user import User


class TransactionType(factory.django.DjangoModelFactory):
    class Meta:
        model = TransactionTypeModel

    name = factory.Sequence(lambda n: f"Transaction Type {n}")
    icon = "Savings"
    color = "#006CD1"
    created_by = factory.SubFactory(User)
    updated_by = factory.SelfAttribute("created_by")


class IncomeTransactionType(TransactionType):
    name = "Income"
    icon = "Savings"
    color = "#006CD1"


class ExpensesTransactionType(TransactionType):
    name = "Expenses"
    icon = "Payments"
    color = "#E5484D"


class TransferTransactionType(TransactionType):
    name = "Transfer"
    icon = "Transfer"
    color = "#F5A524"
