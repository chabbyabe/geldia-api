from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from ledger.models import TransactionType as TransactionTypeModel
from tests.factories.ledger.transaction_type import (
    IncomeTransactionType,
    ExpensesTransactionType,
    TransferTransactionType,
)

User = get_user_model()

class Command(BaseCommand):
    help = "Seed database with initial data"

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding database...\n")

        # Create/get system user (avoid duplicates)
        system_user, _ = User.objects.get_or_create(
            username="system",
            defaults={"email": "system@example.com"},
        )

        # Seed transaction types
        self.seed_transaction_type(1, IncomeTransactionType, system_user)
        self.seed_transaction_type(2, ExpensesTransactionType, system_user)
        self.seed_transaction_type(3, TransferTransactionType, system_user)

        self.stdout.write(self.style.SUCCESS("\nSeeding completed ✅"))

    def seed_transaction_type(self, pk, factory_class, user):
        data = factory_class.build()

        obj, created = TransactionTypeModel.objects.update_or_create(
            id=pk,
            defaults={
                "name": data.name,
                "icon": data.icon,
                "color": data.color,
                "created_by": user,
                "updated_by": user,
            },
        )

        action = "Created" if created else "Updated"
        self.stdout.write(f"{action}: {obj.name}")