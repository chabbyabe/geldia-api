from __future__ import annotations

from typing import Any

from rest_framework import serializers

from ledger.models import Category, TransactionType
from ledger.serializers.transaction_types import TransactionTypeSimpleSerializer
from users.serializers import UserSimpleSerializer

class CategorySerializer(serializers.ModelSerializer):
    created_by = UserSimpleSerializer(read_only=True)
    updated_by = UserSimpleSerializer(read_only=True)    
    deleted_by = UserSimpleSerializer(read_only=True)
    transaction_type = TransactionTypeSimpleSerializer(read_only=True)
    parent_category = serializers.SerializerMethodField()
    transaction_type_id = serializers.PrimaryKeyRelatedField(
        queryset=TransactionType.objects.all(),
        source="transaction_type",
        write_only=True,
        required=False,
        allow_null=True,
    )
    parent_category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source="parent_category",
        write_only=True,
        required=False,
        allow_null=True,
    )

    def get_parent_category(self, obj: Category) -> dict[str, Any] | None:
        if obj.parent_category:
            return {
                "id": obj.parent_category.id,
                "name": obj.parent_category.name,
                "color": obj.parent_category.color,
                "icon": obj.parent_category.icon,
            }
        return None

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        instance = getattr(self, "instance", None)
        parent_category = attrs.get(
            "parent_category",
            instance.parent_category if instance else None,
        )
        transaction_type = attrs.get(
            "transaction_type",
            instance.transaction_type if instance else None,
        )

        if parent_category is not None:
            parent_transaction_type = parent_category.transaction_type

            if transaction_type != parent_transaction_type:
                raise serializers.ValidationError({
                    "transaction_type_id": (
                        "Child categories must use the same transaction type as their parent category."
                    )
                })

        return attrs

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


class CategoryTreeSerializer(CategorySimpleSerializer):
    children = serializers.SerializerMethodField()
    created_by = UserSimpleSerializer(read_only=True)
    updated_by = UserSimpleSerializer(read_only=True)    
    
    class Meta(CategorySimpleSerializer.Meta):
        fields = [
            'id',
            'name',
            'color',
            'icon',
            'notes',
            'transaction_type',
            'created_by',
            'created_at',
            'updated_by',
            'updated_at',
            'parent_category',
            'children',
        ]

    def get_children(self, obj: Category) -> list[dict[str, Any]]:
        children = getattr(obj, "prefetched_children", obj.category_set.all())
        return CategorySimpleSerializer(children, many=True).data



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
