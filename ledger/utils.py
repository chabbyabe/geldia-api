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


def get_or_create_instance(
    model: type[TModel],
    name: str | None,
    user: User,
    defaults: dict[str, Any] | None = None,
) -> TModel | None:
    if not name:
        return None
    final_defaults = defaults if defaults else {}
    instance, _ = model.objects.get_or_create(
        name=name.strip().title(),
        defaults={**final_defaults, 'created_by': user}
    )
    return instance


def clear_validated_keys(
    validated_data: dict[str, Any],
    keys_to_clear: list[str],
) -> None:
    """
    Sets the specified keys in validated_data to None if they exist.

    Args:
        validated_data (Dict[str, Any]): Serializer's validated_data dictionary.
        keys_to_clear (List[str]): List of keys to reset to None.

    Returns:
        None
    """
    for key in keys_to_clear:
        if key in validated_data:
            validated_data[key] = None


def serialize_for_json(data: dict[str, Any] | None) -> dict[str, JSONValue] | None:
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
        start_date = timezone.make_aware(timezone.datetime.strptime(start_date, "%Y-%m-%d")) if start_date else None
        end_date = timezone.make_aware(timezone.datetime.strptime(end_date, "%Y-%m-%d")) if end_date else None
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
