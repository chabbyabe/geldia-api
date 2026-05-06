import json
import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from ledger.models import Place, Store, Tag
from ledger.models import TransactionType as TransactionTypeModel
from tests.factories.ledger.transaction_type import (
    ExpensesTransactionType,
    IncomeTransactionType,
    TransferTransactionType,
)
from ledger.utils import smart_title

User = get_user_model()


class Command(BaseCommand):
    help = "Seed database with initial data (transaction types, categories, places, stores, tags)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--created-by-id",
            type=int,
            help="User id to assign as created_by for imported categories.",
        )

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
        self.stdout.write(self.style.SUCCESS(f"{action}: {obj.name}"))

    # -------------------------
    # PLACES
    # -------------------------
    def seed_places(self):
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
                name=item["name"].title(),
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
                name=smart_title(item["name"]),
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

        for item in data:
            Tag.objects.update_or_create(
                name=smart_title(item),
                defaults={
                    "color": "#006CD1",
                    "created_at": now,
                }
            )

        self.stdout.write(self.style.SUCCESS("Tags imported successfully"))

    def parse_int(self, value):
        if value in (None, ""):
            return None
        return int(value)

    def get_seed_user_id(self, created_by_id=None):
        if created_by_id is not None:
            if User.objects.filter(id=created_by_id).exists():
                return created_by_id
            raise CommandError(f"User with id {created_by_id} does not exist.")

        users = list(
            User.objects.order_by("id").values("id", "username", "email", "first_name", "last_name")
        )

        if not users:
            raise CommandError("No users found. Create a user before seeding categories.")

        self.stdout.write("Select the user to assign as created_by for imported categories:")
        for user in users:
            full_name = f'{user["first_name"]} {user["last_name"]}'.strip() or "-"
            username = user["username"] or "-"
            email = user["email"] or "-"
            self.stdout.write(
                f'  {user["id"]}: {username} | {email} | {full_name}'
            )

        while True:
            value = input("Enter created_by_id: ").strip()
            parsed_id = self.parse_int(value)

            if parsed_id is None:
                self.stdout.write(self.style.WARNING("Please enter a valid user id."))
                continue

            if User.objects.filter(id=parsed_id).exists():
                return parsed_id

            self.stdout.write(self.style.WARNING(f"User with id {parsed_id} does not exist."))
