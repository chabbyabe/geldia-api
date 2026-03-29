from __future__ import annotations

from typing import Any

from rest_framework import serializers

from ledger.models import Category
from ledger.serializers.transaction_types import TransactionTypeSimpleSerializer


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "deleted_at"]


class CategorySimpleSerializer(serializers.ModelSerializer):
    transaction_type = TransactionTypeSimpleSerializer(read_only=True)
    parent_category = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'color', 'icon', 'transaction_type', 'parent_category']
        read_only_fields = ['id']

    def get_parent_category(self, obj: Category) -> dict[str, Any] | None:
        if obj.parent_category:
            return {
                "id": obj.parent_category.id,
                "name": obj.parent_category.name,
                "color": obj.parent_category.color,
                "icon": obj.parent_category.icon,
            }
        return None
    

class CategoryOverviewSerializer(serializers.ModelSerializer):
    name = serializers.CharField()
    icon = serializers.CharField()
    color = serializers.CharField()
    is_parent = serializers.BooleanField()
    amount = serializers.FloatField()
    formatted_amount = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "name",
            "icon",
            "color",
            "is_parent",
            "amount",
            "formatted_amount",
        ]

    def get_formatted_amount(self, obj: dict[str, Any]) -> str:
        return f"€{(obj['amount'] or 0):,.2f}"
