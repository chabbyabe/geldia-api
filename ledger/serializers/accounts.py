from __future__ import annotations

from typing import Any

from rest_framework import serializers

from users.models import Account, User
from users.serializers import UserSimpleSerializer
from ledger.models import Category
from ledger.serializers.categories import CategorySimpleSerializer


class AccountSerializer(serializers.ModelSerializer):
    user = UserSimpleSerializer(read_only=True)
    shared_users = UserSimpleSerializer(many=True, read_only=True)
    shared_user_ids = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        many=True,
        write_only=True,
        source="shared_users",
        required=False,
    )
    categories = CategorySimpleSerializer(many=True, read_only=True)
    category_ids = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        many=True,
        write_only=True,
        source="categories",
        required=False,
    )
    has_transactions = serializers.SerializerMethodField()
    transactions = serializers.SerializerMethodField()
    class Meta:
        model = Account
        exclude = ['created_by', 'updated_by', 'deleted_by']
        read_only_fields = ['id', 'created_at', 'updated_at', 'deleted_at']
 
    def get_has_transactions(self, obj: Account) -> bool:
        return obj.transactions.exists()
    
    def get_transactions(self, obj: Account):
        from ledger.serializers.transactions import TransactionSerializer
        transactions = obj.transactions.order_by("-transaction_at")[:5]
        return TransactionSerializer(transactions, many=True).data

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        request = self.context["request"]
        instance = self.instance

        is_default = attrs.get("is_default")

        if is_default is True:
            qs = Account.objects.filter(
                user=request.user,
                is_default=True
            )

            if instance:
                qs = qs.exclude(pk=instance.pk)

            if qs.exists():
                raise serializers.ValidationError(
                    "You already have a default account."
                )

        return attrs


class AccountSimpleSerializer(serializers.ModelSerializer):
    categories = CategorySimpleSerializer(many=True, read_only=True)
    class Meta:
        model = Account
        fields = ["id", "name", "icon", "color", "balance", "is_default", "is_savings", "user_id", "categories"]
        read_only_fields = ["id", "created_at", "updated_at", "deleted_at"]

     
