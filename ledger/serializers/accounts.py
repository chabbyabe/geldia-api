from __future__ import annotations

from typing import Any

from rest_framework import serializers

from users.models import Account, User
from users.serializers import UserSimpleSerializer


class AccountSerializer(serializers.ModelSerializer):
    user = UserSimpleSerializer(read_only=True)
    shared_users = UserSimpleSerializer(many=True, read_only=True)
    shared_user_ids = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        many=True,
        write_only=True,
        source="shared_users"
    )

    has_transactions = serializers.SerializerMethodField()
    class Meta:
        model = Account
        exclude = ['created_by', 'updated_by', 'deleted_by']
        read_only_fields = ['id', 'created_at', 'updated_at', 'deleted_at']
 
    def get_has_transactions(self, obj: Account) -> bool:
        return obj.transactions.exists()

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
    class Meta:
        model = Account
        fields = ["id", "name", "icon", "color", "balance", "is_default", "user_id"]
        read_only_fields = ["id", "created_at", "updated_at", "deleted_at"]

     
