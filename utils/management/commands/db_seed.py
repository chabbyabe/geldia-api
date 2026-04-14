from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from ledger.models import TransactionType as TransactionTypeModel
from tests.factories.ledger.transaction_type import (
    IncomeTransactionType,
    ExpensesTransactionType,
    TransferTransactionType,
)
import json
import os
from django.conf import settings
from ledger.models import Place, Store, Tag
from django.core.management.base import BaseCommand
from django.utils import timezone

User = get_user_model()

class Command(BaseCommand):
    help = "Seed database with initial data (places + transaction types)"

    def handle(self, *args, **options):
        self.stdout.write("Seeding database...\n")

        self.seed_transaction_types()
        self.seed_places()
        self.seed_stores()
        self.seed_tags()

        self.stdout.write(self.style.SUCCESS("\nSeeding completed ✅"))

    # -------------------------
    # TRANSACTION TYPES
    # -------------------------
    def seed_transaction_types(self):
        self.stdout.write("Seeding transaction types...")

        self.seed_transaction_type(1, IncomeTransactionType)
        self.seed_transaction_type(2, ExpensesTransactionType)
        self.seed_transaction_type(3, TransferTransactionType)

    def seed_transaction_type(self, pk, factory_class):
        data = factory_class.build()

        obj, created = TransactionTypeModel.objects.update_or_create(
            id=pk,
            defaults={
                "name": data.name,
                "icon": data.icon,
                "color": data.color,
            },
        )

        action = "Created" if created else "Updated"
        self.stdout.write(f"{action}: {obj.name}")

    # -------------------------
    # PLACES
    # -------------------------
    def seed_places(self):
        self.stdout.write("Importing places...")

        file_path = os.path.join(
            settings.BASE_DIR,
            "utils",
            "data",
            "places",
            "netherlands-places.json",
        )

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        objects = [
            Place(
                name=item["name"],
                classification=item["classification"],
            )
            for item in data
        ]

        Place.objects.bulk_create(
            objects,
            ignore_conflicts=True,
            batch_size=1000,
        )

        self.stdout.write(self.style.SUCCESS("Places imported successfully"))


    # -------------
    # STORES
    # -------------
    def seed_stores(self, *args, **options):
        file_path = os.path.join(
            settings.BASE_DIR,
            "utils",
            "data",
            "stores",
            "netherlands-stores.json"
        )

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        objects = [
            Store(
                name=item["name"],
                classification=item["classification"],
                created_at=timezone.now(),
            )
            for item in data
        ]

        Store.objects.bulk_create(
            objects,
            ignore_conflicts=True,
            batch_size=1000
        )

        self.stdout.write(self.style.SUCCESS("Stores imported successfully"))

    # -------------
    # TAGS
    # -------------
    def seed_tags(self, *args, **options):
        file_path = os.path.join(
            settings.BASE_DIR,
            "utils",
            "data",
            "tags.json"
        )

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        data = list(dict.fromkeys(data))

        now = timezone.now()

        objects = [
            Tag(
                name=item,
                color="#006CD1",
                created_at=now,
            )
            for item in data
        ]

        Tag.objects.bulk_create(
            objects,
            update_conflicts=True,
            unique_fields=["name"],
            update_fields=["color"],
            batch_size=1000
        )

        self.stdout.write(self.style.SUCCESS("Tags imported successfully"))