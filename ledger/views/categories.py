from __future__ import annotations

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from core.pagination import CustomPageNumberPagination
from core.viewsets.mixins import UserAuditMixin
from ledger.models import Category
from ledger.serializers.categories import CategorySerializer

class CategoryViewSet(viewsets.ModelViewSet, UserAuditMixin):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination
    http_method_names = ["get", "post", "patch", "delete"]

    # Get only for the authenticated user's own account
    def get_queryset(self):
        return Category.objects.filter(created_by=self.request.user)

    # Create only for authenticated users
    def perform_create(self, serializer) -> None:
        serializer.save(created_by=self.request.user)
