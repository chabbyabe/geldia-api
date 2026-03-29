from __future__ import annotations

from django.db.models import Q
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from core.pagination import CustomPageNumberPagination
from core.viewsets.mixins import UserAuditMixin
from ledger.serializers.accounts import AccountSerializer
from users.models import Account

class AccountViewSet(viewsets.ModelViewSet, UserAuditMixin):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination
    http_method_names = ['get', 'post', 'patch', 'delete']

    # Get only for the authenticated user's own account
    def get_queryset(self):
        user = self.request.user
        return (
            Account.objects
            .visible_to(user)
            .distinct().order_by('-is_default', '-created_at')
        )
    
    def perform_create(self, serializer) -> None:
        serializer.save(user=self.request.user)
