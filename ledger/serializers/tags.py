from __future__ import annotations

from rest_framework import serializers

from ledger.models import Tag


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "deleted_at"]


class TagSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "color"]
        read_only_fields = ["id"]
