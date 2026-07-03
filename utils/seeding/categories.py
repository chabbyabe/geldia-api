import json
import os
from django.conf import settings
from django.db import transaction
from ledger.models import Category, TransactionType

from ledger.utils.common import smart_title


# -------------------------
# CATEGORIES
# -------------------------
def seed_categories_for_user(user_id, stdout=None):
    file_path = os.path.join(
        settings.BASE_DIR,
        "utils",
        "data",
        "categories.json",
    )

    def log(msg):
        if stdout:
            stdout.write(msg)

    if not os.path.exists(file_path):
        log(f"Categories file not found, skipping: {file_path}")
        return

    log("Importing categories...")

    with open(file_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    table_data = next(
        (
            item["data"]
            for item in payload
            if item.get("type") == "table" and item.get("name") == "ledger_category"
        ),
        None,
    )

    if table_data is None:
        log("No ledger_category table data found, skipping categories")
        return

    categories_by_source_id = {}
    transaction_type_ids = set(
        TransactionType.objects.filter(pk__in={
            int(row["transaction_type_id"])
            for row in table_data
            if row.get("transaction_type_id") is not None
        }).values_list("id", flat=True)
    )

    with transaction.atomic():
        for row in table_data:
            source_category_id = int(row["id"])
            source_transaction_type_id = row.get("transaction_type_id")
            transaction_type_id = (
                int(source_transaction_type_id)
                if source_transaction_type_id is not None
                and int(source_transaction_type_id) in transaction_type_ids
                else None
            )
            defaults = {
                "name": smart_title(row["name"]),
                "notes": row.get("notes"),
                "color": row.get("color"),
                "icon": row.get("icon"),
                "transaction_type_id": transaction_type_id,
                "created_by_id": user_id,
            }

            category = Category.all_objects.filter(
                created_by_id=user_id,
                name=defaults["name"],
            ).first()

            if category is None:
                category = Category.all_objects.create(**defaults)
            else:
                for field, value in defaults.items():
                    setattr(category, field, value)
                category.save()

            categories_by_source_id[source_category_id] = category

        # handle parent relationships
        for row in table_data:
            source_category_id = int(row["id"])
            category = categories_by_source_id[source_category_id]
            source_parent_id = row.get("parent_category_id")

            parent_category = (
                categories_by_source_id.get(int(source_parent_id))
                if source_parent_id is not None
                else None
            )

            Category.all_objects.filter(id=category.id).update(
                parent_category_id=parent_category.id if parent_category else None,
            )

    log(f"Categories imported successfully ({len(categories_by_source_id)})")
