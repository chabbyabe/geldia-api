from __future__ import annotations

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from core.pagination import CustomPageNumberPagination
from core.viewsets.mixins import UserAuditMixin
from ledger.models import Tag
from ledger.serializers.tags import TagSerializer

from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from ledger.filters import MUIBaseFilterBackend
from ledger.constants import BaseFilterType


class TagFilter(MUIBaseFilterBackend):
    date_field = None
    empty_string_fields = ["name"]
    filter_type = BaseFilterType.TAG

class TagViewSet(UserAuditMixin, viewsets.ModelViewSet):
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination
    http_method_names = ["get", "post", "patch", "delete"]

    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter,
        TagFilter
    ]

    search_fields = [
        "name",
        "color",
    ]

    def get_queryset(self):
        return Tag.objects.filter(created_by=self.request.user)