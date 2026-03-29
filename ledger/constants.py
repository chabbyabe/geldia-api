from dataclasses import dataclass

@dataclass(frozen=True)
class TxnType:
    INCOME: str = "Income"
    EXPENSES: str = "Expenses"
    TRANSFER: str = "Transfer"
