from __future__ import annotations
from rest_framework import serializers
from django.utils import timezone

def year_bounds():
    current_year = timezone.now().year
    return current_year - 3, current_year + 3


def is_valid_year(year: int) -> bool:
    min_year, max_year = year_bounds()
    return min_year <= year <= max_year

class IncomeReportSerializer(serializers.Serializer):
    selected_year = serializers.IntegerField(required=False)
    compare_year = serializers.IntegerField(required=False)

    def validate(self, data):
        selected = data.get("selectedYear")
        compare = data.get("compareYear")

        if selected is not None and compare is not None:

            if selected == compare:
                raise serializers.ValidationError({
                    "compareYear": "Cannot be the same as selectedYear."
                })

            if compare >= selected:
                raise serializers.ValidationError({
                    "compareYear": "Must be earlier than selectedYear."
                })

        return data
        

    def get_selected_year(self) -> int:
        return int(self.validated_data.get("selectedYear", timezone.now().year))

    def get_compare_year(self) -> int | None:
        return self.validated_data.get("compareYear", None)
