from __future__ import annotations

from typing import Any, Protocol

from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.exceptions import PermissionDenied


class SaveSerializer(Protocol):
    validated_data: dict[str, Any]
    instance: Any

    def save(self, **kwargs: Any) -> Any:
        ...


class UserAuditMixin:
    """
    Mixin to automatically set created_by, updated_by, deleted_by
    and optionally enforce ownership for models with a 'user' field.
    """

    def perform_create(self, serializer: SaveSerializer) -> None:
        user = self.request.user
        save_kwargs: dict[str, Any] = {
            "created_by": user,
            "created_at": timezone.now(),
            "updated_at": timezone.now(),
        }

        # Only add 'user' if the serializer accepts it
        if "user" in serializer.validated_data:
            save_kwargs["user"] = user

        serializer.save(**save_kwargs)

    def perform_update(self, serializer: SaveSerializer) -> None:
        instance = serializer.instance
        if hasattr(instance, "user") and instance.user != self.request.user:
            raise PermissionDenied("You cannot update this object")
        serializer.save(
            updated_by=self.request.user,
            updated_at=timezone.now())

    def perform_destroy(self, instance: Any) -> None:
        if hasattr(instance, "user") and instance.user != self.request.user:
            raise PermissionDenied("You cannot delete this object")

        # Use soft-delete if available
        if hasattr(instance, "deleted_at") and hasattr(instance, "deleted_by"):
            instance.deleted_at = timezone.now()
            instance.deleted_by = self.request.user
            instance.save()
        else:
            instance.delete()

class AppModelViewSet(
    viewsets.GenericViewSet,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    UserAuditMixin,
):
    pass
