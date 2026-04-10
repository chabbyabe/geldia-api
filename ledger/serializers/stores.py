from __future__ import annotations

from rest_framework import serializers
from ledger.models import Store
from users.serializers import UserSimpleSerializer


class StoreSerializer(serializers.ModelSerializer):
    created_by = UserSimpleSerializer(read_only=True)

    class Meta:
        model = Store
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "deleted_at"]

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        name = attrs.get("name")

        if user and user.is_authenticated and name:
            existing = Store.objects.filter(
                created_by=user,
                name__iexact=name.strip(),
            )

            instance = getattr(self, "instance", None)
            if instance is not None:
                existing = existing.exclude(pk=instance.pk)

            if existing.exists():
                raise serializers.ValidationError({"name": "Store already exists."})

        return attrs
class StoreSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = ["id", "name"]
        read_only_fields = ["id"]
