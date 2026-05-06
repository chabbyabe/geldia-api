from __future__ import annotations

from django.db.models import Case, When, Value, IntegerField
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
            .annotate(
                is_owner=Case(
                    When(user=user, then=Value(1)),
                    default=Value(0),
                    output_field=IntegerField(),
                )
            )
            .order_by(
                '-is_owner', 
                '-is_default',
                '-created_at',
            )
            .distinct()
        )
    
    def perform_create(self, serializer) -> None:
        serializer.save(user=self.request.user)
