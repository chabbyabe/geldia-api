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
