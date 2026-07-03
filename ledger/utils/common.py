
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, TypeVar

from django.db.models import Model
from django.utils import timezone

from ledger.constants import DateRange
from users.models import User

TModel = TypeVar("TModel", bound=Model)
JSONScalar = str | int | float | bool | None
JSONValue = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]


def smart_title(name: str) -> str:
    words = name.strip().split()

    return " ".join(
        word if not word.islower() else word.title()
        for word in words
    )


def normalize_import_header(header: str) -> str:
    return " ".join(header.strip().lower().split())


def normalize_category(name):
    if not name:
        return "other"
    return name.strip().lower()


def get_or_create_instance(
    model: type[TModel],
    name: str | None,
    user: User,
    defaults: dict[str, Any] | None = None,
    filter_by_user: bool = False,
) -> TModel | None:
    if not name:
        return None

    final_defaults = defaults or {}
    lookup = {
        **({"created_by": user} if filter_by_user else {}),
        "name": smart_title(name),
    }

    instance = model.objects.filter(**lookup).first()

    if instance:
        return instance

    kwargs = {
        **lookup,
        **final_defaults,
    }

    if not filter_by_user:
        kwargs["created_by"] = user

    return model.objects.create(**kwargs)


def clear_validated_keys(
    validated_data: dict[str, Any],
    keys_to_clear: list[str],
) -> None:
    """
    Sets the specified keys in validated_data to None if they exist.

    Args:
        validated_data (Dict[str, Any]): Serializer's validated_data dict.
        keys_to_clear (List[str]): List of keys to reset to None.

    Returns:
        None
    """
    for key in keys_to_clear:
        if key in validated_data:
            validated_data[key] = None


def serialize_for_json(
        data: dict[str, Any] | None) -> dict[str, JSONValue] | None:
    """
    Convert Decimal and date/datetime values
    to JSON-serializable formats.
    """
    if not data:
        return data

    serialized: dict[str, JSONValue] = {}

    for key, value in data.items():
        if isinstance(value, Decimal):
            serialized[key] = str(value)  # safer for financial data
        elif isinstance(value, (date, datetime)):
            serialized[key] = value.isoformat()
        else:
            serialized[key] = value

    return serialized


def get_date_range(
    request: Any,
    filter_type: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> tuple[date | datetime | None, date | datetime | None]:

    try:
        start_date = timezone.make_aware(timezone.datetime.strptime(
            start_date, "%Y-%m-%d")) if start_date else None
        end_date = timezone.make_aware(timezone.datetime.strptime(
            end_date, "%Y-%m-%d")) if end_date else None
    except ValueError:
        start_date = end_date = None

    today = timezone.now().date()
    if filter_type == DateRange.WEEK:
        start_date = today - timedelta(days=today.weekday())  # start of week
        end_date = start_date + timedelta(days=6)
    elif filter_type == DateRange.MONTH:
        start_date = today.replace(day=1)
        next_month = start_date.replace(day=28) + timedelta(days=4)
        end_date = next_month - timedelta(days=next_month.day)
    elif filter_type == DateRange.YEAR:
        start_date = today.replace(month=1, day=1)
        end_date = today.replace(month=12, day=31)

    return start_date, end_date


def is_keyword_present(keywords: list[str], text: str) -> bool:
    text_lower = text.lower()
    return any(k.lower() in text_lower for k in keywords)
