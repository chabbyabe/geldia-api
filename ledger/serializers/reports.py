from __future__ import annotations
from rest_framework import serializers
from django.utils import timezone


def year_bounds():
    current_year: int = timezone.now().year
    return current_year - 3, current_year + 3


def is_valid_year(year: int) -> bool:
    min_year: int
    max_year: int
    min_year, max_year = year_bounds()
    return min_year <= year <= max_year


class ReportParamRequestSerializer(serializers.Serializer):
    selectedYear = serializers.IntegerField(required=False)
    compareYear = serializers.IntegerField(required=False)

    def validate(self, data):
        selected: int | None = data.get("selectedYear")
        compare: int | None = data.get("compareYear")

        if selected and compare:
            if selected == compare:
                raise serializers.ValidationError({
                    "compareYear": "Cannot be the same as selectedYear."
                })

            if compare >= selected:
                raise serializers.ValidationError({
                    "compareYear": "Must be earlier than selectedYear."
                })

        return data

    def get_selected_year(self):
        return int(self.validated_data.get(
            "selectedYear", timezone.now().year))

    def get_compare_year(self):
        return self.validated_data.get("compareYear")


class IncomeCompanySerializer(serializers.Serializer):
    name = serializers.CharField()
    gross_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    net_amount = serializers.DecimalField(max_digits=12, decimal_places=2)


class IncomeMonthSerializer(serializers.Serializer):
    month = serializers.IntegerField()
    month_label = serializers.CharField()
    gross_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    net_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    companies = IncomeCompanySerializer(many=True)


class IncomeReportResponseSerializer(serializers.Serializer):
    selected_year = serializers.IntegerField()
    compare_year = serializers.IntegerField(allow_null=True, required=False)
    base_data = IncomeMonthSerializer(many=True)
    compare_data = IncomeMonthSerializer(many=True, allow_null=True,
                                         required=False)


class CategoryExpenseSerializer(serializers.Serializer):
    color = serializers.CharField(max_length=20)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)


class ParentCategoryExpenseSerializer(serializers.Serializer):
    categories = serializers.DictField(
        child=CategoryExpenseSerializer()
    )
    total = serializers.DecimalField(max_digits=12, decimal_places=2)


class ExpensesReportSerializer(serializers.Serializer):
    month = serializers.IntegerField()
    date = serializers.CharField()
    parent_categories = serializers.DictField(
        child=ParentCategoryExpenseSerializer()
    )
    total = serializers.DecimalField(max_digits=12, decimal_places=2)


class ExpensesReportResponseSerializer(serializers.Serializer):
    selected_year = serializers.IntegerField()
    compare_year = serializers.IntegerField(allow_null=True, required=False)
    base_data = ExpensesReportSerializer(many=True)
    compare_data = ExpensesReportSerializer(many=True, allow_null=True,
                                            required=False)
