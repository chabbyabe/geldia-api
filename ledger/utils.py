from __future__ import annotations

import csv
import io
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, TypeVar

from django.db.models import Model
from django.utils import timezone

from ledger.constants import DateRange
from users.models import User
from ledger.constants import IMPORT_TXN_HEADER_ALIASES, CREDIT_TRANSFER_LOOKUP
import re

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


def parse_import_decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None

    cleaned = value.strip().replace(".", "").replace(",", ".")
    if not cleaned:
        return None

    try:
        return abs(Decimal(cleaned))
    except Exception:
        return None


def parse_import_date(value: str | None) -> datetime | None:
    if not value:
        return None

    cleaned = value.strip()
    for fmt in ("%Y%m%d", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            naive = datetime.strptime(cleaned, fmt)
            return timezone.make_aware(naive)
        except ValueError:
            continue

    return None

def parse_transaction_import_file(uploaded_file: Any) -> list[dict[str, Any]]:
    """
    Supports:
    - uploaded CSV file objects
    - dict with one CSV header key and one CSV row value
    """

    # Handle special dict input
    if isinstance(uploaded_file, dict):
        if not uploaded_file:
            return []

        header = list(uploaded_file.keys())[0]
        row = list(uploaded_file.values())[0]
        decoded = f"{header}\n{row}"

    else:
        raw_bytes = uploaded_file.read()

        decoded = None
        for encoding in ("utf-8-sig", "cp1252", "latin-1"):
            try:
                decoded = raw_bytes.decode(encoding)
                break
            except UnicodeDecodeError:
                continue

        if decoded is None:
            raise ValueError("Could not decode the uploaded file.")

    sample = decoded[:2048]

    try:
        delimiter = csv.Sniffer().sniff(sample, delimiters="\t;,").delimiter
    except csv.Error:
        delimiter = ";"

    reader = csv.DictReader(io.StringIO(decoded), delimiter=delimiter)

    if not reader.fieldnames:
        raise ValueError("The uploaded file is missing a header row.")

    normalized_headers = {
        header: IMPORT_TXN_HEADER_ALIASES.get(normalize_import_header(header), header)
        for header in reader.fieldnames
        if header is not None
    }

    rows: list[dict[str, Any]] = []

    for index, row in enumerate(reader, start=1):
        mapped_row = {
            normalized_headers.get(key, key): (value.strip() if isinstance(value, str) else value)
            for key, value in row.items()
            if key is not None
        }

        name = mapped_row.get("name", "")
        code = mapped_row.get("code", "")
        payment_type = mapped_row.get("payment_type", "")

        transaction_at = parse_import_date(mapped_row.get("date"))
        amount = parse_import_decimal(mapped_row.get("amount"))
        transfer_type = (mapped_row.get("transfer_type") or "").strip().lower()
        balance_after = parse_import_decimal(mapped_row.get("balance_after"))
        
        if not transaction_at or amount is None:
            continue

        # Check the notes if it contains an Oranje spaarrekening then if exists get the account number
        notes = mapped_row.get("notes", "")
        match = re.search(r"(?:Oranje spaarrekening|Beleggingsrek.)\s+(\S+)", notes)
        savings_account = match.group(1) if match else None

        # Set transaction type
        if savings_account:
            transaction_type_name = "Transfer"
        elif transfer_type in CREDIT_TRANSFER_LOOKUP:
            transaction_type_name = "Income"
        else:
            transaction_type_name = "Expenses"

        rows.append(
            {
                "index": index,
                "transaction_at": transaction_at,
                "amount": amount,
                "transaction_type_name": transaction_type_name,
                "name": name,
                "notes": notes,
                "payment_type": payment_type,
                "code": code,
                "balance_after": balance_after,
                "counterparty_account": mapped_row.get("counterparty_account") or "",
                "account_number": mapped_row.get("account_number") or "",
                "tag": mapped_row.get("tag") or "",
                "savings_account": savings_account
            }
        )

    return rows

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
