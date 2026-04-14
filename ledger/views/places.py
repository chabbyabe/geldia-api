from __future__ import annotations

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from core.pagination import CustomPageNumberPagination
from core.viewsets.mixins import UserAuditMixin
from ledger.models import Place
from ledger.serializers.places import PlaceSerializer
from django.db.models import Q

from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from ledger.filters import MUIBaseFilterBackend
from ledger.constants import BaseFilterType

class PlaceFilter(MUIBaseFilterBackend):
    date_field = None
    empty_string_fields = ["name", "classification"]
    filter_type = BaseFilterType.PLACE

class PlaceViewSet(UserAuditMixin, viewsets.ModelViewSet):
    serializer_class = PlaceSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination
    http_method_names = ["get", "post", "patch", "delete"]

    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter,
        PlaceFilter
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
        return Place.objects.all()