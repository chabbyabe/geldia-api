from __future__ import annotations

from rest_framework import serializers

from ledger.models import Store


class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "deleted_at"]

class StoreSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = ["id", "name"]
        read_only_fields = ["id"]
