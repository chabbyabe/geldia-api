from __future__ import annotations

from django.db.models import Case, When, Value, IntegerField
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

from core.pagination import CustomPageNumberPagination
from core.viewsets.mixins import UserAuditMixin
from ledger.constants import UserAction
from ledger.models import AccountLog
from ledger.serializers.accounts import AccountSerializer
from ledger.utils import serialize_for_json
from users.models import Account


def serialize_account_snapshot(account: Account) -> dict:
    return serialize_for_json(
        {
            "id": account.id,
            "name": account.name,
            "icon": account.icon,
            "color": account.color,
            "balance": account.balance,
            "count_in_assets": account.count_in_assets,
            "is_default": account.is_default,
            "is_savings": account.is_savings,
            "is_shared": account.is_shared,
            "notes": account.notes,
            "user_id": account.user_id,
            "shared_user_ids": list(
                account.shared_users.values_list("id", flat=True)),
            "category_ids": list(
                account.categories.values_list("id", flat=True)),
        }
    )


def log_account(
    *,
    account: Account,
    action: str,
    performed_by,
    old_data: dict | None = None,
    new_data: dict | None = None,
) -> None:
    AccountLog.objects.create(
        account=account,
        action=action,
        performed_by=performed_by,
        old_data=old_data,
        new_data=new_data,
    )


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
        instance = serializer.save(user=self.request.user)
        log_account(
            account=instance,
            action=UserAction.CREATE,
            performed_by=self.request.user,
            new_data=serialize_account_snapshot(instance),
        )

    def perform_update(self, serializer) -> None:
        instance = serializer.instance
        if instance.user != self.request.user:
            raise PermissionDenied("You cannot update this object")

        old_data = serialize_account_snapshot(instance)
        instance = serializer.save(updated_by=self.request.user)
        log_account(
            account=instance,
            action=UserAction.UPDATE,
            performed_by=self.request.user,
            old_data=old_data,
            new_data=serialize_account_snapshot(instance),
        )

    def perform_destroy(self, instance: Account) -> None:
        if instance.user != self.request.user:
            raise PermissionDenied("You cannot delete this object")

        old_data = serialize_account_snapshot(instance)
        instance.deleted_by = self.request.user
        instance.deleted_at = timezone.now()
        instance.save(update_fields=["deleted_by", "deleted_at", "updated_at"])
        log_account(
            account=instance,
            action=UserAction.DELETE,
            performed_by=self.request.user,
            old_data=old_data,
        )
