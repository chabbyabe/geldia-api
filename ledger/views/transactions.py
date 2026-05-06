from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from core.pagination import CustomPageNumberPagination
from rest_framework.response import Response
from users.models import Account
from ledger.models import Transaction, Tag, Category, Place, Store, TransactionType, TransactionLog
from ledger.serializers.transactions import TransactionSerializer
from ledger.serializers.accounts import AccountSimpleSerializer
from ledger.serializers.categories import CategorySimpleSerializer
from ledger.serializers.tags import TagSimpleSerializer
from ledger.serializers.places import PlaceSimpleSerializer
from ledger.serializers.stores import StoreSimpleSerializer
from ledger.serializers.transaction_types import TransactionTypeSimpleSerializer
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from ledger.filters import MUIBaseFilterBackend
from core.viewsets.mixins import UserAuditMixin
from django.db import transaction
from decimal import Decimal
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from ledger.constants import TxnType, UserAction, BaseFilterType
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone
from ledger.utils import (
    get_or_create_instance,
    clear_validated_keys,
    parse_transaction_import_file,
    serialize_for_json,
    smart_title,
    is_keyword_present
)
from django.shortcuts import get_object_or_404
from django.db.models import Q
from ledger.constants import IMPORT_TXN_CATEGORIES, PAYMENT_TYPES_LOOKUP
from typing import Optional
from difflib import SequenceMatcher

try:
    from rapidfuzz import fuzz
except ModuleNotFoundError:
    fuzz = None

def log_transaction(instance : any, action: str, created: bool = False, **kwargs):
    """
    Logs a transaction action: created, updated, or deleted.

    Parameters:
    - instance: Transaction instance being acted upon
    - action: UserAction "created", "updated", or "deleted"
    - created: True if this is a creation event
    """
    from ledger.serializers.transactions import TransactionSerializer

    new_data = serialize_for_json(TransactionSerializer(instance).data)
    
    performed_by = None
    old_data = None

    if action in [UserAction.UPDATE, UserAction.DELETE]:
        old_data = (
            TransactionLog.objects
            .filter(transaction=instance.pk)
            .order_by('-created_at')
            .values_list('new_data', flat=True)
            .first()
        )
        performed_by = (
            instance.updated_by if action == UserAction.UPDATE
            else instance.deleted_by
        )
    else:
        performed_by = instance.created_by

    # Create the transaction log
    TransactionLog.objects.create(
        transaction=instance,
        action=action if not created else UserAction.CREATE,
        old_data=old_data,
        new_data=new_data,
        performed_by=performed_by
    )

class TransactionFilterBackend(MUIBaseFilterBackend):
    date_field = "transaction_at"
    empty_string_fields = ["name", "notes", "store__name", "place__name"]
    filter_type = BaseFilterType.TRANSACTION

def _clean_name(name: str):
    return name.replace("NLD", "").strip()

def _get_first_word(value: str) -> str | None:
    parts = value.split()
    return smart_title(" ".join(parts[:1])) if parts else None

def _get_last_word(value: str) -> str | None:
    parts = value.split()
    return parts[-1].title() if parts else None

def build_import_notes(row):
    note_parts = [row.get("notes", "")]

    if row.get("payment_type"):
        note_parts.append(f"Payment Type: {row['payment_type']}")
    if row.get("code"):
        note_parts.append(f"Code: {row['code']}")

    return " | ".join(part for part in note_parts if part)[:500] or None

def build_import_place(row):
    code = row.get("code")
    if code not in PAYMENT_TYPES_LOOKUP:
        return None
    name = _clean_name(row.get("name", ""))

    # Exclude place if keyword are found
    exlude_keywords = ("www.ovpay.nl",)
    if is_keyword_present(exlude_keywords, name):
        return None
    
    return _get_last_word(name)


def build_import_store(row):
    code = row.get("code")
    if code not in PAYMENT_TYPES_LOOKUP:
        return None

    name = _clean_name(row.get("name", ""))

    # Exclude place if keyword are found
    exclude_keywords = ("www.ovpay.nl",)
    if is_keyword_present(exclude_keywords, name):
        return None
        
    store = _get_first_word(name)
    place = _get_last_word(name)

    if place and store:
        store = store.replace(place, "").strip()

    return store
    

def normalize_text(text: str) -> str:
    text = (text or "").lower()
    words = text.split()
    return " ".join(words[:3])

def match_import_category(text: str, lookup: dict[str, str]) -> Optional[str]:
    text = normalize_text(text)

    best_match = None
    best_score = 0

    for key, value in lookup.items():
        key_norm = normalize_text(key)

        if fuzz is not None:
            score = fuzz.partial_ratio(text, key_norm)
        else:
            score = int(SequenceMatcher(None, text, key_norm).ratio() * 100)

        if score > best_score:
            best_score = score
            best_match = value

    # tune threshold if needed
    return best_match if best_score >= 90 else None


def build_import_category(row: dict) -> str:
    name = row.get("name", "")
    notes = row.get("notes", "")
    transaction_type_name = (row.get("transaction_type_name") or "").lower()
    code = (row.get("code", "")).strip()

    if code == "OV" and transaction_type_name == "transfer":
        return "Savings"
    
    # Check if there is salary indication in the description
    salary_keywords = ("salary", "salaris")
    refund_keywords = ("refund", "return", "returned", "cashback","retour", 
                       "retourpintransactie", "geretourneerd", "terugbetaling")
    allowance_keywords = ("allowance", "teruggaaf", "voorschot", "toeslag", )
    gift_keywords = ("gift", "present", "donation", "cadeau", "schenking", "zakgeld", "extraatje", "geschenk")
    subscription_keywords = ("subscription", "abonnement", "abonnementen")
    
    if is_keyword_present(salary_keywords, notes):
        return "Salary"
    
    if is_keyword_present(refund_keywords, notes):
        return "Refund"
    
    if is_keyword_present(allowance_keywords, notes):
        return "Allowance"
    
    if is_keyword_present(gift_keywords, notes):
        return "Gift"
     
    if is_keyword_present(subscription_keywords, notes):
        return "Subscriptions"
    
    category = match_import_category(name, IMPORT_TXN_CATEGORIES)
    
    if category:
        return category

    return "Others"


def import_transaction_exists(*, user, account_id: int, row: dict[str, object]) -> bool:
    transaction_type_name = row["transaction_type_name"]
    amount = row["amount"]
    transaction_at = row["transaction_at"]
    name = row["name"]

    queryset = Transaction.objects.visible_to(user).filter(
        account_id=account_id,
        transaction_type__name=transaction_type_name,
        name=name,
        transaction_at=transaction_at,
    )

    if transaction_type_name == TxnType.INCOME:
        return queryset.filter(
            Q(net_amount=amount) | Q(amount=amount)
        ).exists()

    return queryset.filter(amount=amount).exists()


class ImportTransactionsView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        uploaded_file = request.FILES.get("file")
        account_id = request.data.get("account_id") or request.data.get("account")
        user = request.user

        if not uploaded_file:
            return Response({"detail": "file is required."}, status=400)
        if not account_id:
            return Response({"detail": "account_id is required."}, status=400)

        try:
            parsed_rows = parse_transaction_import_file(uploaded_file)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)

        if not parsed_rows:
            return Response({"detail": "No importable transactions were found in the uploaded file."}, status=400)

        transaction_type_map = {
            txn_type.name: txn_type
            for txn_type in TransactionType.objects.filter(
                name__in=[TxnType.INCOME, TxnType.EXPENSES, TxnType.TRANSFER]
            )
        }
        created_ids = []
        skipped_count = 0
        ordered_rows = sorted(parsed_rows, key=lambda row: (row["transaction_at"], row["index"]))
        savings_category = Category.objects.filter(name="Savings", created_by=user).first()

        with transaction.atomic():
            viewset = TransactionViewSet()
            viewset.request = request

            for row in ordered_rows:
                # exists = import_transaction_exists(
                #     user=user,
                #     account_id=int(account_id),
                #     row=row,
                # )
                exists = False

                if exists:
                    skipped_count += 1
                    continue
                else:
                    transaction_type = transaction_type_map[row["transaction_type_name"]]
                
                    savings_account = row.get('savings_account', None)
                    # If there is a savings account, use it
                    if savings_account:
                        account_instance = get_or_create_instance(
                            Account, savings_account, user, 
                                defaults={'is_default': False, "is_shared": False, "is_savings": True, 
                                          "count_in_assets": False, "user_id": user.id }, 
                                filter_by_user=True,
                            )
                        account_instance.categories.set([savings_category])
                        transaction_type =  transaction_type_map[row["transaction_type_name"]]
                    
                    is_income = row["transaction_type_name"] == TxnType.INCOME
                    is_transfer = row["transaction_type_name"] == TxnType.TRANSFER

                    payload = {
                        "account_id": account_id,
                        "user_id": user.id,
                        "transaction_type_id": transaction_type.id,
                        "amount": str(row["amount"]),
                        "net_amount": str(row["amount"]) if is_income else None,
                        "debit_month_year": row["transaction_at"].strftime("%Y-%m-%d") if is_income else None,
                        "name": row["name"],
                        "place_name": build_import_place(row) or None,
                        "store_name": build_import_store(row) or None,
                        "tags_names": [row["tag"]] if row["tag"] else [],
                        "category_name": build_import_category(row) or None,
                        "notes": build_import_notes(row),
                        "transaction_at": row["transaction_at"],
                        "pair_transaction": is_transfer and account_instance.id,
                    }

                    serializer = TransactionSerializer(data=payload, context={"request": request})
                    serializer.is_valid(raise_exception=True)

                    instance = viewset.create_transaction_from_data(serializer, payload)
                    created_ids.append(instance.id)
                
        return Response(
            {
                "created_count": len(created_ids),
                "skipped_count": skipped_count,
                "created_ids": created_ids,
            },
            status=201,
        )

class TransactionViewSet(viewsets.ModelViewSet, UserAuditMixin):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination
    http_method_names = ['get', 'post', 'patch', 'delete']

    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter,
        TransactionFilterBackend
    ]

    search_fields = [
        "name",
        "notes",
        "store__name",
        "place__name",
    ]

    ordering_fields = [
        "id",
        "amount",
        "name",
        "store__name",
        "account__name",
        "tags__name",
        "transaction_type__name",
        "category__name",
        "place__name",
        "transaction_at",
        "net_amount",
        "gross_amount",
        "debit_month_year"
    ]

    def get_queryset(self):
        return (
            Transaction.objects
            .prefetch_related("tags")
            .select_related(
                "user",
                "store",
                "category",
                "place",
                "account",
                "transaction_type"
            )
            .visible_to(self.request.user)
        )

    def validate_debit_month_year(self, value):
        # If frontend sends "2026-01"
        if isinstance(value, str) and len(value) == 7:
            return timezone.make_aware(timezone.datetime.strptime(value, "%Y-%m")).date()
        return value

    def _get_account_id_from_payload(self, data):
        account_id = data.get("account") or data.get("account_id")
        if not account_id:
            raise ValidationError({"account_id": "This field is required."})
        return int(account_id)

    def _get_locked_account_for_user(self, account_id):
        return Account.objects.select_for_update().get(
            pk=account_id, deleted_at__isnull=True)

    def _get_locked_accounts_for_user(self, account_ids):
        accounts = list(
            Account.objects.select_for_update().filter(
                pk__in=account_ids,
                deleted_at__isnull=True,
            )
        )
        account_map = {account.pk: account for account in accounts}
        return account_map

    def create_transaction_from_data(self, serializer, data):
        user = self.request.user
        account_id = self._get_account_id_from_payload(data)
        amount = Decimal(data.get("amount") or 0)
        transaction_type = TransactionType.objects.get(
            pk=data.get("transaction_type_id")
        )
        transaction_type_name = transaction_type.name
        with transaction.atomic():
            store_instance = get_or_create_instance(Store, data.get("store"), user)
            place_instance = get_or_create_instance(Place, data.get("place"), user)
            
            account = get_object_or_404(Account, pk=account_id)
            if 'category' in data and data.get("category") != None:
                category_instance = get_or_create_instance(
                    Category, data.get("category"), user, {
                        "transaction_type": transaction_type,
                    }) if data.get("category") else instance.category
                account.categories.add(category_instance)
            else:
                category_instance = None

            if transaction_type_name == TxnType.INCOME:
                net_amount = Decimal(data.get("net_amount", 0) or 0)
                account = self._get_locked_account_for_user(account_id)

                previous_balance = account.balance
                account.balance += net_amount
                account.save()

                serializer.validated_data.update({
                    "previous_balance": previous_balance
                })

                clear_validated_keys(serializer.validated_data, ["pair_transaction", "amount"])

            elif transaction_type_name == TxnType.EXPENSES:
                account = self._get_locked_account_for_user(account_id)

                previous_balance = account.balance

                if account.balance < amount:
                    raise ValidationError({
                        "non_field_errors": ["Insufficient funds"]
                    })
                account.balance -= amount
                account.save()

                serializer.validated_data.update({
                    "previous_balance": previous_balance
                })

                clear_validated_keys(serializer.validated_data,
                                    ["pair_transaction", "net_amount", "gross_amount", "debit_month_year"])

            elif transaction_type_name ==  TxnType.TRANSFER:
                pair_id = int(data.get("pair_transaction"))

                if account_id == pair_id:
                    raise ValidationError("Cannot transfer to the same account")

                account_map = self._get_locked_accounts_for_user([account_id, pair_id])
                from_acc = account_map.get(account_id)
                to_acc = account_map.get(pair_id)

                if not from_acc or not to_acc:
                    raise ValidationError("Invalid account(s)")

                if from_acc.balance < amount:
                    raise ValidationError({
                        "non_field_errors": ["Insufficient funds"]
                    })
                from_previous = from_acc.balance
                to_previous = to_acc.balance

                from_acc.balance -= amount
                to_acc.balance += amount

                from_acc.save()
                to_acc.save()

                serializer.validated_data.update({
                    "previous_balance": from_previous,
                    "pair_previous_balance": to_previous,
                    "pair_transaction": to_acc
                })

                account = from_acc

                clear_validated_keys(serializer.validated_data,
                                    ["net_amount", "gross_amount", "debit_month_year"])

            instance = serializer.save(
                user=self.request.user,
                account=account,
                created_by=self.request.user,
                store=store_instance,
                place=place_instance,
                category=category_instance,
            )

        log_transaction(instance=instance, action=UserAction.CREATE, created=True)

        return instance
    
    def perform_create(self, serializer):
        self.create_transaction_from_data(serializer, self.request.data)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        data = request.data
        user = request.user

        account_id = data.get("account") or data.get("account_id") or instance.account_id
        transaction_type_id = data.get("transaction_type_id", instance.transaction_type_id)
        transaction_type = TransactionType.objects.get(pk=transaction_type_id)
        transaction_type_name = transaction_type.name 
        pair_transaction_id = data.get("pair_transaction", getattr(instance, "pair_transaction_id", None))
        pair_transaction_id = int(pair_transaction_id) if pair_transaction_id else None

        new_amount = Decimal(data.get("amount") or instance.amount or 0)        
        
        with transaction.atomic():

            # Update related instances if provided
            if 'store' in data and data.get("store") != None:
                store_instance = get_or_create_instance(
                    Store, data.get("store"), user) if data.get("store") else instance.store
            else:
                store_instance = None

            if 'place' in data and data.get("place") != None:
                place_instance = get_or_create_instance(
                    Place, data.get("place"), user) if data.get("place") else instance.place
            else:
                place_instance = None

            account = get_object_or_404(Account, pk=account_id)
            if 'category' in data and data.get("category") != None:
                category_instance = get_or_create_instance(
                    Category, data.get("category"), user, {
                        "transaction_type": transaction_type,
                    }) if data.get("category") else instance.category
                account.categories.add(category_instance)
            else:
                category_instance = None

            if 'tags' in data:
                if data.get("tags") is not None:
                    tags_instances = [
                        get_or_create_instance(Tag, tag, user)
                        for tag in data.get("tags")
                    ]
                else:
                    tags_instances = []
            else:
                tags_instances = None

            # Lock all possible accounts
            account_ids = {instance.account_id, account_id}
            if instance.pair_transaction_id:
                account_ids.add(instance.pair_transaction_id)
            if pair_transaction_id:
                account_ids.add(pair_transaction_id)

            account_map = self._get_locked_accounts_for_user(account_ids)

            # REVERSE OLD TRANSACTION
            old_account = account_map.get(instance.account_id)

            if instance.transaction_type.name == TxnType.INCOME:
                old_account.balance -= instance.net_amount

            elif instance.transaction_type.name == TxnType.EXPENSES:
                old_account.balance += instance.amount

            elif instance.transaction_type.name == TxnType.TRANSFER:
                old_pair = account_map.get(instance.pair_transaction_id)
                old_account.balance += instance.amount
                old_pair.balance -= instance.amount
                old_pair.save()

            old_account.save()

            # Apply new transaction
            new_account = account_map.get(account_id)

            if transaction_type_name == TxnType.INCOME:
                new_net = Decimal(data.get("net_amount", instance.net_amount or 0))
                prev_balance = new_account.balance
                new_account.balance += new_net

                data["previous_balance"] = prev_balance

            elif transaction_type_name == TxnType.EXPENSES:
                if new_account.balance < new_amount:
                    raise ValidationError({
                        "non_field_errors": ["Insufficient funds"]
                    })
                prev_balance = new_account.balance
                new_account.balance -= new_amount

                data["previous_balance"] = prev_balance

            elif transaction_type_name == TxnType.TRANSFER:
                pair_account = account_map.get(pair_transaction_id)

                if new_account.balance < new_amount:
                    raise ValidationError({
                        "non_field_errors": ["Insufficient funds"]
                    })
                from_prev = new_account.balance
                to_prev = pair_account.balance

                new_account.balance -= new_amount
                pair_account.balance += new_amount

                pair_account.save()

                data["previous_balance"] = from_prev
                data["pair_previous_balance"] = to_prev
                data["pair_transaction"] = pair_transaction_id

            new_account.save()

            serializer = self.get_serializer(instance, data=data, partial=True)
            serializer.is_valid(raise_exception=True)
            save_kwargs = {"updated_by": request.user}
            if store_instance is not None:
                save_kwargs["store"] = store_instance
            if place_instance is not None:
                save_kwargs["place"] = place_instance
            if category_instance is not None:
                save_kwargs["category"] = category_instance
            serializer.save(**save_kwargs)

            if tags_instances is not None:
                instance.tags.set(tags_instances)

        log_transaction(instance=instance, action=UserAction.UPDATE)
        return Response(serializer.data)

    def perform_destroy(self, instance):
        transaction_type = instance.transaction_type.name

        with transaction.atomic():
            # INCOME → subtract the previously added net_amount
            if transaction_type == TxnType.INCOME and instance.account_id and instance.net_amount:
                account = Account.objects.select_for_update().get(pk=instance.account_id)
                previous_balance = account.balance
                account.balance -= Decimal(instance.net_amount)
                account.save()

            # EXPENSES → add back the previously deducted amount
            elif transaction_type == TxnType.EXPENSES and instance.account_id and instance.amount:
                account = Account.objects.select_for_update().get(pk=instance.account_id)
                previous_balance = account.balance
                account.balance += Decimal(instance.amount)
                account.save()

            # TRANSFER → reverse both sides
            elif transaction_type == TxnType.TRANSFER:
                if not instance.account_id or not instance.pair_transaction_id:
                    raise ValidationError("Invalid transfer accounts")

                accounts = Account.objects.select_for_update().filter(
                    pk__in=[instance.account_id, instance.pair_transaction_id]
                )
                account_dict = {acc.pk: acc for acc in accounts}

                from_account = account_dict.get(instance.account_id)
                to_account = account_dict.get(instance.pair_transaction_id)

                if not from_account or not to_account:
                    raise ValidationError("Invalid account(s)")

                amount = Decimal(instance.amount or 0)
                
                # Save previous balances
                previous_balance = from_account.balance
                to_prev = to_account.balance

                # Reverse transfer
                from_account.balance += amount
                to_account.balance -= amount

                from_account.save()
                to_account.save()

                instance.pair_previous_balance = to_prev
                
            instance.previous_balance = previous_balance
            instance.save()
            
            log_transaction(instance=instance, action=UserAction.DELETE)

            # Finally delete the transaction
            instance.delete()


class GetInitialTransactionDataView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        # Fetch the user's data
        accounts = (Account.objects.visible_to(user)
                    .distinct()
                    .order_by('-is_default', '-created_at')
                    .prefetch_related("categories")
                    )
        categories = Category.objects.filter(
                        accounts__in=accounts
                    ).distinct()
        tags = Tag.objects.all()
        stores = Store.objects.all()
        places = Place.objects.all()

        # Serialize the data
        data = {
            "accounts": AccountSimpleSerializer(accounts, many=True).data,
            "categories": CategorySimpleSerializer(categories, many=True).data,
            "tags": TagSimpleSerializer(tags, many=True).data,
            "stores": StoreSimpleSerializer(stores, many=True).data,
            "places": PlaceSimpleSerializer(places, many=True).data,
            "transaction_types" : TransactionTypeSimpleSerializer(
                TransactionType.objects.all(), many=True).data
        }

        return Response(data)
