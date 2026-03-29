from __future__ import annotations

from rest_framework import serializers

from ledger.models import TransactionType


class TransactionTypeSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransactionType
        fields = ["id", "name", "icon", "color"]
        read_only_fields = ["id"]
