from __future__ import annotations

from typing import Any, Callable

from rest_framework import serializers

from ledger.models import Category, Place, Store, Tag, Transaction, TransactionType
from ledger.serializers.accounts import AccountSimpleSerializer
from ledger.serializers.categories import CategorySimpleSerializer
from ledger.serializers.places import PlaceSimpleSerializer
from ledger.serializers.stores import StoreSimpleSerializer
from ledger.serializers.tags import TagSimpleSerializer
from ledger.serializers.transaction_types import TransactionTypeSimpleSerializer
from ledger.utils import get_or_create_instance
from users.models import Account, User
from users.serializers import UserSimpleSerializer


class CreateIfNotExistsRelatedField(serializers.PrimaryKeyRelatedField):
    def __init__(
        self,
        queryset: Any,
        slug_field: str = "name",
        extra_create_data: Callable[[], dict[str, Any] | None] | dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """
        extra_create_data can be a dict or a callable that returns a dict.
        """
        self.slug_field = slug_field
        self.extra_create_data = extra_create_data
        super().__init__(queryset=queryset, **kwargs)

    def to_internal_value(self, data: Any) -> Any:
        # Existing PK
        if isinstance(data, int):
            return super().to_internal_value(data)

        # String -> get_or_create
        if isinstance(data, str):
            lookup = {self.slug_field: data}
            defaults = {}
            # If extra_create_data is callable, call it with the serializer context
            if callable(self.extra_create_data):
                defaults = self.extra_create_data()
            elif isinstance(self.extra_create_data, dict):
                defaults = self.extra_create_data

            obj, _ = self.queryset.get_or_create(defaults=defaults, **lookup)
            return obj

        raise serializers.ValidationError(f"Invalid value for {self.slug_field}")

class TransactionSerializer(serializers.ModelSerializer):
    user = UserSimpleSerializer(read_only=True)
    store = StoreSimpleSerializer(read_only=True)
    category = CategorySimpleSerializer(read_only=True)
    place = PlaceSimpleSerializer(read_only=True)
    account = AccountSimpleSerializer(read_only=True)
    pair_transaction = AccountSimpleSerializer(read_only=True)
    transaction_type = TransactionTypeSimpleSerializer(read_only=True)
    tags = TagSimpleSerializer(many=True, read_only=True)
    formatted_amount = serializers.SerializerMethodField()
    formatted_net_amount = serializers.SerializerMethodField()
    formatted_gross_amount = serializers.SerializerMethodField()

    # ID fields for writes
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        write_only=True, 
        source="user"
    )
    account_id = serializers.PrimaryKeyRelatedField(
        queryset=Account.objects.all(), 
        write_only=True, 
        source="account"
    )
    transaction_type_id = serializers.PrimaryKeyRelatedField(
        queryset=TransactionType.objects.all(),
        write_only=True, 
        source="transaction_type"
    )
    category_name = CreateIfNotExistsRelatedField(
        queryset=Category.objects.all(),
        slug_field="name",
        write_only=True,
        extra_create_data=lambda: None,
        required=False,
        allow_null=True
    )
    store_name = CreateIfNotExistsRelatedField(
        queryset=Store.objects.all(), 
        slug_field="name",
        write_only=True,
        extra_create_data=lambda: None,
        required=False,
        allow_null=True

    )
    place_name = CreateIfNotExistsRelatedField(
        queryset=Place.objects.all(),
        slug_field="name",
        write_only=True,
        extra_create_data=lambda: None,
        required=False,
        allow_null=True
    )
    tags_names = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        allow_empty=True
    )

    class Meta:
        model = Transaction
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "deleted_at"]

    def get_formatted_amount(self, obj: Transaction) -> str:
        return f"€{(obj.amount or 0):,.2f}"
    
    def get_formatted_net_amount(self, obj: Transaction) -> str:
        return f"€{(obj.net_amount or 0):,.2f}"
    
    def get_formatted_gross_amount(self, obj: Transaction) -> str:
        return f"€{(obj.gross_amount or 0):,.2f}"
    
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # Bind the callable dynamically at runtime
        self.fields["category_name"].extra_create_data = self._category_extra_data
        self.fields["place_name"].extra_create_data = self._place_extra_data
        self.fields["store_name"].extra_create_data = self._store_extra_data

    def _category_extra_data(self) -> dict[str, Any]:
        transaction_type_id = self.initial_data.get("transaction_type_id")
        if not transaction_type_id:
            raise serializers.ValidationError("transaction_type_id is required to create category")
        
        # Convert ID to instance
        try:
            transaction_type = TransactionType.objects.get(id=transaction_type_id)
        except TransactionType.DoesNotExist:
            raise serializers.ValidationError("Invalid transaction_type_id")

        return {"transaction_type": transaction_type, "created_by": self.context["request"].user}

    def _store_extra_data(self) -> dict[str, Any]:
        return {"created_by": self.context["request"].user}
    
    def _place_extra_data(self) -> dict[str, Any]:
        return {"created_by": self.context["request"].user}
    
    def create(self, validated_data: dict[str, Any]) -> Transaction:
        # Pop the virtual fields

        category = validated_data.pop("category_name", None)
        store = validated_data.pop("store_name", None)
        place = validated_data.pop("place_name", None)
        tags = validated_data.pop("tags_names", None)
        # Create the Transaction instance normally
        transaction = Transaction.objects.create(**validated_data)
        # Assign the popped related objects
        if category:
            transaction.category = category
        if store:
            transaction.store = store
        if place:
            transaction.place = place

        if tags is not None:
            tag_ids = []
            for name in tags:
                tag = get_or_create_instance(Tag, name, self.context["request"].user)
                if tag is not None:
                    tag_ids.append(tag.id)
    
            transaction.tags.set(tag_ids)

        transaction.save()
        return transaction
