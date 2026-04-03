from __future__ import annotations

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet
from ledger.serializers.transaction_logs import TransactionLogSerializer
from ledger.models import TransactionLog
from core.pagination import CustomPageNumberPagination
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from ledger.filters import MUIBaseFilterBackend
from ledger.constants import BaseFilterType

json_field : str = "new_data__"

class TransactionLogFilterBackend(MUIBaseFilterBackend):
    date_field = "created_at"
    empty_string_fields = ["some_text_field"]
    filter_type = BaseFilterType.TRANSACTION_LOG
    json_field = "new_data"

class TransactionLogViewSet(GenericViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination
    serializer_class = TransactionLogSerializer

    filter_backends = [    
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter,
        TransactionLogFilterBackend
    ]
    
    
    search_fields = [
        f"{json_field}name",
        f"{json_field}notes",
        f"{json_field}store__name",
        f"{json_field}place__name",
        f"{json_field}category__name",
        f"{json_field}tags__name",
    ]

    ordering_fields = [
        "id",
        "action",
        f"{json_field}id",
        f"{json_field}name",
        f"{json_field}acount__name",
        f"{json_field}category__name",
        f"{json_field}transaction_type__name",
        f"{json_field}transaction",
        f"{json_field}store__name",
        f"{json_field}place__name",
        f"{json_field}transaction_at",
        f"{json_field}amount",
        f"{json_field}net_amount",
        f"{json_field}gross_amount",
        f"{json_field}debit_month_year",
        f"{json_field}pair_transaction__name",
        "created_at"
    ]

    ordering = ['-created_at']

    def get_queryset(self):
        return TransactionLog.objects.filter(performed_by=self.request.user)

    @action(detail=False, methods=['get'], url_path="transactions")
    def transaction_logs(self, request):
        queryset = self.get_queryset()
        queryset = self.filter_queryset(queryset)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = TransactionLogSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = TransactionLogSerializer(queryset, many=True)
        return Response(serializer.data)