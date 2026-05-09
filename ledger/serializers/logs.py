from __future__ import annotations

from rest_framework import serializers

from ledger.models import TransactionLog
from ledger.serializers.accounts import AccountSimpleSerializer
from ledger.serializers.categories import CategorySimpleSerializer
from ledger.serializers.tags import TagSimpleSerializer
from ledger.serializers.places import PlaceSimpleSerializer
from ledger.serializers.stores import StoreSimpleSerializer
from ledger.serializers.transaction_types import TransactionTypeSimpleSerializer
from users.serializers import UserSimpleSerializer
from ledger.serializers.transactions import TransactionSerializer
from ledger.models import AccountLog
from ledger.serializers.accounts import AccountSimpleSerializer
from users.models import Account
from users.serializers import UserSimpleSerializer


class AccountLogSerializer(serializers.ModelSerializer):
    performed_by = UserSimpleSerializer(read_only=True)
    account = AccountSimpleSerializer(read_only=True)
    account_id = serializers.PrimaryKeyRelatedField(
        queryset=Account.objects.all(),
        source="account",
        write_only=True,
        required=False,
    )

    class Meta:
        model = AccountLog
        fields = [
            "id",
            "account",
            "account_id",
            "action",
            "performed_by",
            "old_data",
            "new_data",
            "note",
            "created_at",
        ]
        read_only_fields = ["id", "performed_by", "created_at"]

class TransactionLogSerializer(serializers.ModelSerializer):
    performed_by = UserSimpleSerializer(read_only=True)
    store = StoreSimpleSerializer(read_only=True)
    category = CategorySimpleSerializer(read_only=True)
    place = PlaceSimpleSerializer(read_only=True)
    account = AccountSimpleSerializer(read_only=True)
    pair_transaction = AccountSimpleSerializer(read_only=True)
    transaction_type = TransactionTypeSimpleSerializer(read_only=True)
    tags = TagSimpleSerializer(many=True, read_only=True)
    transaction = TransactionSerializer(read_only=True)


    class Meta:
        model = TransactionLog
        fields = "__all__"
        read_only_fields = ["id"]


