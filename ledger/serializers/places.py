from __future__ import annotations

from rest_framework import serializers

from ledger.models import Place
from users.serializers import UserSimpleSerializer

class PlaceSerializer(serializers.ModelSerializer):
    created_by = UserSimpleSerializer(read_only=True)

    class Meta:
        model = Place
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "deleted_at"]

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        name = attrs.get("name")

        if user and user.is_authenticated and name:
            existing = Place.objects.filter(
                created_by=user,
                name__iexact=name.strip(),
            )

            instance = getattr(self, "instance", None)
            if instance is not None:
                existing = existing.exclude(pk=instance.pk)

            if existing.exists():
                raise serializers.ValidationError("Place already exists.")

        return attrs

class PlaceSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Place
        fields = ["id", "name"]
        read_only_fields = ["id"]
