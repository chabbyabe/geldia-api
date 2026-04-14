from __future__ import annotations

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from core.pagination import CustomPageNumberPagination
from core.viewsets.mixins import UserAuditMixin
from ledger.models import Store
from ledger.serializers.stores import StoreSerializer
from django.db.models import Q

from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from ledger.filters import MUIBaseFilterBackend
from ledger.constants import BaseFilterType

class StoreFilter(MUIBaseFilterBackend):
    date_field = None
    empty_string_fields = ["name", "classification"]
    filter_type = BaseFilterType.STORE

class StoreViewSet(UserAuditMixin, viewsets.ModelViewSet):
    serializer_class = StoreSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination
    http_method_names = ["get", "post", "patch", "delete"]


    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter,
        StoreFilter
    ]

    search_fields = [
        "name",
        "classification",
    ]

    ordering_fields = [
        "name",
        "classification",
        "created_by__username",
        "created_at",
        "updated_by__username",
        "updated_at"
    ]

    def get_queryset(self):
        return Store.objects.all()