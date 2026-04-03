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


