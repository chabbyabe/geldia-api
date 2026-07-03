from __future__ import annotations

from django.utils import timezone
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ledger.models import Budget
from ledger.serializers.budgets import BudgetGroupedSerializer, \
    BudgetSerializer
from users.models import Account


class BudgetViewSet(viewsets.ModelViewSet):
    serializer_class = BudgetSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    http_method_names = ["get", "post", "patch", "delete"]

    def get_serializer_class(self):
        if self.action == "list":
            return BudgetGroupedSerializer
        return BudgetSerializer

    def get_queryset(self):
        queryset = (
            Budget.objects.filter(
                account__in=Account.objects.visible_to(self.request.user)
            )
            .select_related("account", "category")
        )
        year = self.request.query_params.get("year") or timezone.now().year
        account_id = self.request.query_params.get("account_id")
        category_id = self.request.query_params.get("category_id")
        month = self.request.query_params.get("month")

        if year:
            queryset = queryset.filter(year=year)
        if account_id:
            queryset = queryset.filter(account_id=account_id)
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        if month:
            queryset = queryset.filter(month=month)

        return queryset.order_by(
            "month", "account__name", "category__name", "id")

    def perform_create(self, serializer) -> None:
        serializer.save(created_by=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = BudgetSerializer(data=request.data,
                                      context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        created = serializer.save(created_by=request.user)

        if isinstance(created, list):
            output = BudgetSerializer(
                created,
                many=True,
                context=self.get_serializer_context(),
            )
            return Response(output.data, status=201)

        output = BudgetSerializer(created,
                                  context=self.get_serializer_context())
        headers = self.get_success_headers(output.data)
        return Response(output.data, status=201, headers=headers)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        grouped_budgets = self._group_budgets(queryset)
        serializer = BudgetGroupedSerializer(grouped_budgets, many=True)
        return Response(serializer.data)

    def perform_update(self, serializer) -> None:
        serializer.save(updated_by=self.request.user)

    def perform_destroy(self, instance) -> None:
        instance.deleted_by = self.request.user
        instance.deleted_at = timezone.now()
        instance.save(update_fields=["deleted_by", "deleted_at", "updated_at"])

    def _group_budgets(self, queryset):
        grouped: dict[tuple[int, int, int], dict] = {}

        for budget in queryset:
            key = (budget.account_id, budget.year, budget.month)
            if key not in grouped:
                grouped[key] = {
                    "account": budget.account,
                    "year": budget.year,
                    "month": budget.month,
                    "categories": [],
                }

            grouped[key]["categories"].append(budget)

        return list(grouped.values())
