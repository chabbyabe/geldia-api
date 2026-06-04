from __future__ import annotations

from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated

from core.pagination import CustomPageNumberPagination
from ledger.constants import BaseFilterType
from ledger.filters import MUIBaseFilterBackend
from ledger.models import AccountLog, TransactionLog
from ledger.serializers.logs import AccountLogSerializer, \
    TransactionLogSerializer
from users.models import Account


json_field: str = "new_data__"


class AccountLogFilterBackend(MUIBaseFilterBackend):
    date_field = "created_at"
    empty_string_fields = ["note"]
    filter_type = BaseFilterType.ACCOUNT_LOG
    json_field = "new_data"


class TransactionLogFilterBackend(MUIBaseFilterBackend):
    date_field = "created_at"
    empty_string_fields = ["note"]
    filter_type = BaseFilterType.TRANSACTION_LOG
    json_field = "new_data"


class AccountLogViewSet(viewsets.ModelViewSet):
    serializer_class = AccountLogSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination
    http_method_names = ["get", "post", "patch", "delete"]
    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter,
        AccountLogFilterBackend,
    ]
    search_fields = [
        f"{json_field}name",
        f"{json_field}notes",
        "note",
    ]
    ordering_fields = [
        "id",
        "action",
        f"{json_field}id",
        f"{json_field}name",
        f"{json_field}balance",
        f"{json_field}is_default",
        f"{json_field}is_savings",
        "created_at",
    ]
    ordering = ["-created_at"]

    def get_queryset(self):
        user = self.request.user
        visible_accounts = Account.objects.visible_to(user)

        return AccountLog.objects.filter(
            Q(account__in=visible_accounts) | Q(performed_by=user)
        ).distinct()

    def _get_visible_account(self, account: Account) -> Account:
        user = self.request.user
        if not Account.objects.visible_to(user).filter(pk=account.pk).exists():
            raise ValidationError({"account_id": [
                "You do not have access to this account."]})
        return account

    def perform_create(self, serializer):
        account = serializer.validated_data.get("account")
        if account is None:
            raise ValidationError({"account_id": ["This field is required."]})

        serializer.save(
            account=self._get_visible_account(account),
            performed_by=self.request.user,
        )

    def perform_update(self, serializer):
        instance = serializer.instance
        if (
            instance.account
            and instance.account.user != self.request.user
            and instance.performed_by != self.request.user
        ):
            raise PermissionDenied("You cannot update this account log")

        account = serializer.validated_data.get("account", instance.account)
        serializer.save(account=self._get_visible_account(
            account) if account else None)

    def perform_destroy(self, instance):
        if (
            instance.account
            and instance.account.user != self.request.user
            and instance.performed_by != self.request.user
        ):
            raise PermissionDenied("You cannot delete this account log")
        instance.delete()


class TransactionLogViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination
    serializer_class = TransactionLogSerializer
    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter,
        TransactionLogFilterBackend,
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
        f"{json_field}pair_account__name",
        "created_at",
    ]
    ordering = ["-created_at"]

    def get_queryset(self):
        user = self.request.user
        return TransactionLog.objects.filter(
            Q(transaction__account__shared_users=user)
            | Q(transaction__account__user=user)
            | Q(performed_by=user)
        ).distinct()
