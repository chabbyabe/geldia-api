from __future__ import annotations

import csv
import io
from datetime import datetime
from decimal import Decimal
from typing import Any, TypeVar

from django.db.models import Model
from django.utils import timezone

from ledger.constants import IMPORT_TXN_HEADER_ALIASES, CREDIT_TRANSFER_LOOKUP
from ledger.utils.common import normalize_import_header
import re

TModel = TypeVar("TModel", bound=Model)
JSONScalar = str | int | float | bool | None
JSONValue = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]


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
        header: IMPORT_TXN_HEADER_ALIASES.get(
            normalize_import_header(header), header)
        for header in reader.fieldnames
        if header is not None
    }

    rows: list[dict[str, Any]] = []

    for index, row in enumerate(reader, start=1):
        mapped_row = {
            normalized_headers.get(
                key, key): (value.strip() if isinstance(value, str) else value)
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

        # Check the notes if it contains an Oranje spaarrekening
        # then if exists get the account number
        notes = mapped_row.get("notes", "")
        match = re.search(r"(?:Oranje spaarrekening|Beleggingsrek.)\s+(\S+)",
                          notes)
        savings_account = match.group(1) if match else None
        is_savings_credit = False
        # Set transaction type
        if savings_account:
            transaction_type_name = "Transfer"
            if transfer_type in CREDIT_TRANSFER_LOOKUP:
                is_savings_credit = True

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
                "transfer_type": transfer_type,
                "balance_after": balance_after,
                "counterparty_account": mapped_row.get(
                    "counterparty_account") or "",
                "account_number": mapped_row.get("account_number") or "",
                "tag": mapped_row.get("tag") or "",
                "savings_account": savings_account,
                "is_savings_credit": is_savings_credit,
            }
        )

    return rows
