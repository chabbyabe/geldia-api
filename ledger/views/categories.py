from __future__ import annotations

from django.db.models import Prefetch
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.pagination import CustomPageNumberPagination
from core.viewsets.mixins import UserAuditMixin
from ledger.models import Category
from ledger.serializers.categories import CategorySerializer, CategoryTreeSerializer

from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from ledger.filters import MUIBaseFilterBackend
from ledger.constants import BaseFilterType

class CategoryFilter(MUIBaseFilterBackend):
    date_field = None
    empty_string_fields = ["name", "notes"]
    filter_type = BaseFilterType.CATEGORY

class CategoryViewSet(UserAuditMixin, viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination
    http_method_names = ["get", "post", "patch", "delete"]

    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter,
        CategoryFilter
    ]

    search_fields = [
        "name",
        "notes",
    ]

    ordering_fields = [
        "icon",
        "transaction_type__name",
        "name",
        "color",
        "created_at"
    ]

    def get_queryset(self):
        base_qs = Category.objects.filter(created_by=self.request.user)
        if self.action in ["list", "retrieve"]:
            return base_qs.select_related("transaction_type").prefetch_related(
                Prefetch(
                    "category_set",
                    queryset=base_qs.select_related("transaction_type", "parent_category"),
                    to_attr="prefetched_children",
                )
            )

        return base_qs

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset()).filter(parent_category__isnull=True)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = CategoryTreeSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = CategoryTreeSerializer(queryset, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        return Response(CategoryTreeSerializer(instance).data)

    def perform_destroy(self, instance):
        if not instance.parent_category:
            instance.delete()
        else:
            instance.parent_category = None
            instance.updated_by = self.request.user
            instance.updated_at = timezone.now()
            instance.save()
