from dataclasses import dataclass

@dataclass(frozen=True)
class TxnType:
    INCOME: str = "Income"
    EXPENSES: str = "Expenses"
    TRANSFER: str = "Transfer"

@dataclass(frozen=True)
class UserAction:
    CREATE: str = "created"
    UPDATE: str = "updated"
    DELETE: str = "deleted"

ACTION_CHOICES: tuple[tuple[str, str], ...] = (
    (UserAction.CREATE, "Created"),
    (UserAction.UPDATE, "Updated"),
    (UserAction.DELETE, "Deleted"),
)

@dataclass(frozen=True)
class DateRange:
    WEEK: str = "Week"
    MONTH: str = "Month"
    YEAR: str = "Year"
    CUSTOM: str = "Custom"


MONTHS : dict[int, str] = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr",
    5: "May", 6: "Jun", 7: "Jul", 8: "Aug",
    9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"
}

@dataclass(frozen=True)
class BaseFilterType:
    TRANSACTION: str = "Transaction"
    TRANSACTION_LOG: str = "TransactionLog"
    CATEGORY: str = "Category"
