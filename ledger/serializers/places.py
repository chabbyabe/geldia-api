from __future__ import annotations

from rest_framework import serializers

from ledger.models import Place


class PlaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Place
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "deleted_at"]


class PlaceSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Place
        fields = ["id", "name"]
        read_only_fields = ["id"]
