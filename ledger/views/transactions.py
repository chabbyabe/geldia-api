from django.db.models import Q
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from core.pagination import CustomPageNumberPagination
from rest_framework.response import Response
from users.models import Account
from ledger.models import Transaction, Tag, Category, Place, Store, TransactionType, TransactionLog
from ledger.serializers.transactions import TransactionSerializer
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from ledger.filters import MUIFilterBackend
from core.viewsets.mixins import UserAuditMixin
from django.db import transaction
from decimal import Decimal
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from ledger.constants import TxnType, UserAction
from rest_framework import serializers
from django.utils import timezone
from ledger.utils import get_or_create_instance, clear_validated_keys, serialize_for_json

def log_transaction(instance : any, action: str, created: bool = False, **kwargs):
    """
    Logs a transaction action: created, updated, or deleted.

    Parameters:
    - instance: Transaction instance being acted upon
    - action: UserAction "created", "updated", or "deleted"
    - created: True if this is a creation event
    """
    from ledger.serializers.transactions import TransactionSerializer

    # Get the latest instance from DB
    current_instance = Transaction.objects.get(pk=instance.pk)
    new_data = serialize_for_json(TransactionSerializer(current_instance).data)

    # Determine old_data for update or delete actions
    old_data = None
    if action in [UserAction.UPDATE, UserAction.DELETE]:
        old_data = (
            TransactionLog.objects
                .order_by('-created_at') 
                .values_list('new_data', flat=True) 
                .filter(transaction=instance.pk)
                .first()
        )

    # Create the transaction log
    TransactionLog.objects.create(
        transaction=instance,
        action=action if not created else UserAction.CREATE,
        old_data=old_data,
        new_data=new_data,
        performed_by=instance.user
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
        MUIFilterBackend
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
            raise serializers.ValidationError({"account_id": "This field is required."})
        return int(account_id)

    def _user_can_access_account(self, account, user):
        return account.user_id == user.id or account.shared_users.filter(pk=user.pk).exists()

    def _get_locked_account_for_user(self, account_id, user):
        account = Account.objects.select_for_update().get(pk=account_id, deleted_at__isnull=True)
        if not self._user_can_access_account(account, user):
            raise serializers.ValidationError("Invalid account(s)")
        return account

    def _get_locked_accounts_for_user(self, account_ids, user):
        accounts = list(
            Account.objects.select_for_update().filter(
                pk__in=account_ids,
                deleted_at__isnull=True,
            )
        )
        account_map = {account.pk: account for account in accounts}

        for account_id in account_ids:
            account = account_map.get(account_id)
            if account is None or not self._user_can_access_account(account, user):
                raise serializers.ValidationError("Invalid account(s)")

        return account_map

    def perform_create(self, serializer):

        data = self.request.data
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
            category_instance = get_or_create_instance(Category, data.get("category"), user, {
                "transaction_type": transaction_type
            })

            if transaction_type_name == TxnType.INCOME:
                net_amount = Decimal(data.get("net_amount", 0) or 0)
                account = self._get_locked_account_for_user(account_id, user)

                previous_balance = account.balance
                account.balance += net_amount
                account.save()

                serializer.validated_data.update({
                    "previous_balance": previous_balance
                })

                clear_validated_keys(serializer.validated_data, ["pair_transaction", "amount"])

            elif transaction_type_name == TxnType.EXPENSES:
                account = self._get_locked_account_for_user(account_id, user)

                previous_balance = account.balance

                if account.balance < amount:
                    raise serializers.ValidationError("Insufficient funds")

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
                    raise serializers.ValidationError("Cannot transfer to the same account")

                account_map = self._get_locked_accounts_for_user([account_id, pair_id], user)
                from_acc = account_map.get(account_id)
                to_acc = account_map.get(pair_id)

                if not from_acc or not to_acc:
                    raise serializers.ValidationError("Invalid account(s)")

                if from_acc.balance < amount:
                    raise serializers.ValidationError("Insufficient funds")

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

            if 'category' in data and data.get("category") != None:
                category_instance = get_or_create_instance(
                    Category, data.get("category"), user, {
                        "transaction_type": transaction_type
                    }) if data.get("category") else instance.category
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

            account_map = self._get_locked_accounts_for_user(account_ids, user)

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
                    raise serializers.ValidationError("Insufficient funds")

                prev_balance = new_account.balance
                new_account.balance -= new_amount

                data["previous_balance"] = prev_balance

            elif transaction_type_name == TxnType.TRANSFER:
                if account_id == pair_transaction_id:
                    raise serializers.ValidationError("Cannot transfer to same account")

                pair_account = account_map.get(pair_transaction_id)

                if new_account.balance < new_amount:
                    raise serializers.ValidationError("Insufficient funds")

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
                    raise serializers.ValidationError("Invalid transfer accounts")

                accounts = Account.objects.select_for_update().filter(
                    pk__in=[instance.account_id, instance.pair_transaction_id]
                )
                account_dict = {acc.pk: acc for acc in accounts}

                from_account = account_dict.get(instance.account_id)
                to_account = account_dict.get(instance.pair_transaction_id)

                if not from_account or not to_account:
                    raise serializers.ValidationError("Invalid account(s)")

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