from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db import transaction
from rest_framework import serializers

from ledger.utils.budgets import calculate_spent_amount, \
    recalculate_budget_spent
from ledger.models import Budget
from ledger.serializers.accounts import AccountOnlySerializer
from ledger.serializers.categories import CategorySimpleSerializer
from ledger.models import Category
from users.models import Account
from users.serializers import UserSimpleSerializer


class BudgetSerializer(serializers.ModelSerializer):
    month = serializers.IntegerField(required=False)
    account = AccountOnlySerializer(read_only=True)
    account_id = serializers.PrimaryKeyRelatedField(
        queryset=Account.objects.filter(deleted_at__isnull=True),
        write_only=True,
        source="account",
        required=False,
    )
    category = CategorySimpleSerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        write_only=True,
        source="category",
        required=False,
    )
    create_full_year = serializers.BooleanField(
        write_only=True,
        required=False,
        default=False,
    )
    remaining_amount = serializers.SerializerMethodField(read_only=True)
    created_by = UserSimpleSerializer(read_only=True)
    updated_by = UserSimpleSerializer(read_only=True)
    deleted_by = UserSimpleSerializer(read_only=True)

    class Meta:
        model = Budget
        fields = "__all__"
        validators = []
        read_only_fields = [
            "id",
            "spent_amount",
            "remaining_amount",
            "created_by",
            "updated_by",
            "deleted_by",
            "created_at",
            "updated_at",
            "deleted_at",
        ]

    def get_remaining_amount(self, obj: Budget) -> Decimal:
        return obj.amount - obj.spent_amount

    def validate_month(self, value: int) -> int:
        if value < 1 or value > 12:
            raise serializers.ValidationError(
                "Month must be between 1 and 12.")
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        instance = getattr(self, "instance", None)
        user = self.context["request"].user
        account = attrs.get("account", instance.account if instance else None)
        category = attrs.get(
            "category", instance.category if instance else None)
        year = attrs.get(
            "year", instance.year if instance else None)
        month = attrs.get(
            "month", instance.month if instance else None)
        create_full_year = self._should_create_full_year(attrs)

        if account is None:
            if instance is None:
                raise serializers.ValidationError({
                    "account_id": "This field is required."
                })
            return attrs
        if category is None:
            if instance is None:
                raise serializers.ValidationError({
                    "category_id": "This field is required."
                })
            return attrs
        if year is None:
            return attrs
        if not create_full_year and month is None:
            return attrs

        if not (
            account.user_id == user.id
            or account.shared_users.filter(pk=user.pk).exists()
        ):
            raise serializers.ValidationError("Invalid account.")

        if category.created_by_id not in (None, user.id):
            raise serializers.ValidationError("Invalid category.")

        if create_full_year:
            existing_months = list(
                Budget.objects.filter(
                    account=account,
                    category=category,
                    year=year,
                )
                .values_list("month", flat=True)
                .order_by("month")
            )
            if existing_months:
                raise serializers.ValidationError(
                    "Yearly budget cannot be created because budgets already "
                    f"exist for month(s): {', '.join(
                        map(str, existing_months))}."
                )
        else:
            qs = Budget.objects.filter(
                account=account,
                category=category,
                year=year,
                month=month,
            )
            if instance is not None:
                qs = qs.exclude(pk=instance.pk)

            if qs.exists():
                raise serializers.ValidationError(
                    "Budget for this account, category, month, "
                    "and year already exists."
                )

        return attrs

    def create(self, validated_data: dict[str, Any]) -> Budget | list[Budget]:
        create_full_year = self._should_create_full_year(validated_data)
        validated_data.pop("create_full_year", None)
        if create_full_year:
            return self._create_full_year(validated_data)

        budget = Budget.objects.create(**validated_data)
        return recalculate_budget_spent(budget)

    def update(self, instance: Budget,
               validated_data: dict[str, Any]) -> Budget:
        validated_data.pop("create_full_year", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return recalculate_budget_spent(instance)

    def _create_full_year(self,
                          validated_data: dict[str, Any]) -> list[Budget]:
        budgets: list[Budget] = []
        with transaction.atomic():
            for month in range(1, 13):
                budget = Budget.objects.create(
                    **validated_data,
                    month=month,
                    spent_amount=calculate_spent_amount(
                        account_id=validated_data["account"].id,
                        category_id=validated_data["category"].id,
                        year=validated_data["year"],
                        month=month,
                    ),
                )
                budgets.append(budget)
        return budgets

    def _should_create_full_year(self, attrs: dict[str, Any]) -> bool:
        if attrs.get("create_full_year"):
            return True

        return self.instance is None and attrs.get("month") is None


class BudgetCategorySerializer(serializers.ModelSerializer):
    budget_id = serializers.IntegerField(source="id", read_only=True)
    category = CategorySimpleSerializer(read_only=True)
    remaining_amount = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Budget
        fields = [
            "budget_id",
            "category",
            "amount",
            "spent_amount",
            "remaining_amount",
        ]
        read_only_fields = fields

    def get_remaining_amount(self, obj: Budget) -> Decimal:
        return obj.amount - obj.spent_amount


class BudgetGroupedSerializer(serializers.Serializer):
    account = AccountOnlySerializer(read_only=True)
    created_by = UserSimpleSerializer(read_only=True)
    year = serializers.IntegerField(read_only=True)
    month = serializers.IntegerField(read_only=True)
    categories = BudgetCategorySerializer(many=True, read_only=True)

    class Meta:
        fields = ["account", "created_by", "year", "month", "categories"]
