from dataclasses import dataclass
from enum import Enum

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
    ACCOUNT_LOG: str = "AccountLog"
    CATEGORY: str = "Category"
    TAG: str = "Tag"
    PLACE: str = "Place"
    STORE: str = "Store"

# Transaction Import
IMPORT_TXN_HEADER_ALIASES: dict[str, str] = {
    # date
    "datum": "date",
    "date": "date",

    # name
    "naam / omschrijving": "name",
    "naam/omschrijving": "name",
    "naam": "name",
    "omschrijving": "name",
    "name / description": "name",
    "name/description": "name",
    "name": "name",
    "description": "name",

    # account
    "rekening": "account_number",
    "account": "account_number",

    # counterparty
    "tegenrekening": "counterparty_account",
    "counterparty": "counterparty_account",
    "counterparty account": "counterparty_account",

    # code
    "code": "code",

    # transfer_type
    "af bij": "transfer_type",
    "af/bij": "transfer_type",
    "debit/credit": "transfer_type",

    # amount
    "bedrag (eur)": "amount",
    "bedrag": "amount",
    "amount": "amount",
    "amount (eur)": "amount",

    # transaction type
    "mutatiesoort": "payment_type",
    "transaction type": "payment_type",

    # notes
    "mededelingen": "notes",
    "notifications": "notes",
    "notes": "notes",

    # balance after
    "saldo na mutatie": "balance_after",
    "resulting balance": "balance_after",
    "balance after": "balance_after",

    "tag": "tag",
}

TXN_PAYMENT_CODES: dict[str, str] = {
    "BA": "Payment Terminal",   # Betaalautomaat
    "IC": "Direct Debit",       # Incasso
    "OV": "Transfer",           # Overschrijving
    "GT": "Online Banking",     # Online bankieren (Manual Transfer)
    "IW": "iDEAL | Wero",       # iDEAL | Wero (In-store withdrawal)
    "ID": "iDEAL",              # iDEAL
    "DV": "Various",            # Diversen
    "VZ": "Batch Payment",      # Verzamelbetaling
    "GM": "Cash Withdrawal",    # Geldautomaat"
    "MA": "Machtiging",         # Machtiging
}

IMPORT_TXN_CATEGORIES: dict[str, str] = {
    # utilities / housing
    "vitens": "Water",
    "energie": "Electricity & Gas",
    "oxxio": "Electricity & Gas",
    "vimexx": "Internet",
    "fiber": "Internet",
    "simpel": "Mobile",
    "kpn": "Mobile",
    "ssh": "Rent",
    "huur": "Rent",
    "oranje": "Savings",
    "notprovided": "Savings",
    "transip": "Internet",

    # insurance / government
    "infomedics": "Health Insurance",
    "de christelijke zorg": "Health Insurance",
    "kosten oranjepakket": "Subscriptions",
    "immigratie en naturalisatie dienst": "Government",


    # groceries
    "kruidvat": "Groceries",
    "hema": "Groceries",
    "jumbo": "Groceries",
    "lidl": "Groceries",
    "albert": "Groceries",
    "amazing oriental": "Groceries",
    "plus": "Groceries",
    "aldi": "Groceries",
    "edeka": "Groceries",
    "spar": "Groceries",
    "alber heijn": "Groceries",
    "ekoplaza": "Groceries",
    "etos": "Groceries",

    # care
    "alvarado cuts": "Care",

    # eating out
    "manneken": "Eat Out",
    "backwerk": "Eat Out",
    "dapp": "Eat Out",
    "mcd": "Eat Out",
    "mcdonalds": "Eat Out",
    "umaimon": "Eat Out",
    "barista": "Eat Out",
    "www.itoshii.nl": "Eat Out",
    "zettle*barista": "Eat Out",
    "bck*kiosk": "Eat Out",
    "i love sushi": "Eat Out",

    # entertainment
    "netflix": "Entertainment",
    "prime video": "Entertainment",
    "hbo": "Entertainment",
    "disney": "Entertainment",
    "disney plus": "Entertainment",

    # electronics
    "sony": "Electronics",
    "samsung": "Electronics",
    "apple": "Electronics",
    "google": "Electronics",
    "huawei": "Electronics",
    "xiaomi": "Electronics",

    # clothing
    "zara": "Clothing",
    "h&m": "Clothing",
    "nike": "Clothing",
    "adidas": "Clothing",
    "asics": "Clothing",
    "reebok": "Clothing",
    "puma": "Clothing",
    "umbro": "Clothing",
    "lacoste": "Clothing",
    "vans": "Clothing",
    "converse": "Clothing",
    "zeeman": "Clothing",
    "c&a": "Clothing",
    "scapino": "Clothing",

    # furniture / home
    "ikea": "Furnitures",

    # transport
    "ns groep": "Transportation",
    "ov chipkaart": "Transportation",
    "www.ovpay.nl": "Transportation",

    # hardware
    "praxis": "Hardware",
    "bck*praxis": "Hardware",
    "solow": "Hardware",
    "intratuin": "Hardware",
    "bck*gamma": "Hardware",

    # gifts / misc retail
    "pay.nl*lindt": "Gift",
    "cycleman": "Others",
    "word international": "Tithes",
    "booking.com": "Travel",
    "booking": "Travel",
    "agoda": "Travel",
    "klm": "Travel",
    "western union": "Gift",
    "rituals": "Gift",
}

PAYMENT_TYPES_LOOKUP = {"BA"}
CREDIT_TRANSFER_LOOKUP = {"bij", "Bij", "Credit", "credit"}
