from __future__ import annotations

from typing import Any

from rest_framework import serializers
from django.utils import timezone


class SummaryOverviewSerializer(serializers.Serializer):
    name = serializers.CharField()
    icon = serializers.CharField()
    color = serializers.CharField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    formatted_amount = serializers.SerializerMethodField()

    def get_formatted_amount(self, obj: dict[str, Any]) -> str:
        return f"€{(obj['amount'] or 0):,.2f}"
    
class YearOverviewQuerySerializer(serializers.Serializer):
    year = serializers.IntegerField(required=False)

    def validate_year(self, value: int) -> int:
        current_year = timezone.now().year
        min_year = current_year - 3
        max_year = current_year + 3

        if not (min_year <= value <= max_year):
            raise serializers.ValidationError(
                f"Year must be between {min_year} and {max_year}."
            )
        return value

    def get_year(self) -> int:
        return int(self.validated_data.get("year", timezone.now().year))
