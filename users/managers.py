from __future__ import annotations

from typing import TYPE_CHECKING, Any
from django.contrib.auth.models import BaseUserManager

if TYPE_CHECKING:
    from .models import User


class UserManager(BaseUserManager["User"]):
    """Custom user manager"""

    def create_user(
        self,
        username: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> "User":

        if not username:
            raise ValueError("Username is required.")

        user = self.model(username=username, **extra_fields)

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.is_staff = False
        user.is_superuser = False

        user.save(using=self._db)
        return user

    def create_superuser(
        self,
        username: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> "User":

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        user = self.create_user(username, password, **extra_fields)

        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)

        return user