from __future__ import annotations

from typing import Any

from rest_framework import permissions


class IsOwnerPermission(permissions.BasePermission):

    def has_object_permission(self, request: Any, view: Any, obj: Any) -> bool:

        # Instance must have an attribute named `owner`.
        return obj.owner == request.user
