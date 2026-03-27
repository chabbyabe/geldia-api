from __future__ import annotations

from typing import Any

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.db.models import Q, UniqueConstraint

from core.models import CommonInfo

from .managers import UserManager
from users.querysets.accounts import AccountQuerySet

class Company(CommonInfo):
    name = models.CharField(max_length=255)

    def __str__(self) -> str:
        return self.name


class User(AbstractBaseUser, PermissionsMixin, CommonInfo):
    """Overriding User model
    Also inherits the CommonInfo model
    """

    first_name = models.CharField(max_length=225)
    last_name = models.CharField(max_length=225)
    username = models.CharField(max_length=50, unique=True, null=True, blank=True)
    email = models.EmailField(max_length=500, unique=True, blank=True, null=True)
    company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        help_text="Work company",
    )
    is_superuser = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ("first_name", "last_name")

    objects = UserManager()

    def __str__(self) -> str:
        return f"{self.username}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self.id:
            self.handle = self.email

        super().save(*args, **kwargs)

    def get_short_name(self) -> str:
        return f"{self.first_name}"

    @property
    def get_full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".title()

    @property
    def get_display_name(self) -> str:
        if self.first_name and self.last_name:
            return self.get_full_name
        return f"{self.email}"

    @property
    def trimmed_email(self) -> str | None:
        if self.email:
            return f"{self.email}".split("@")[0]
        return None


class Account(CommonInfo):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="accounts")
    name = models.CharField(max_length=255)
    icon = models.CharField(max_length=255, null=True, blank=True)
    color = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        default="#006CD1",
        help_text="Hex color, e.g., '123456'",
    )
    balance = models.DecimalField(default=0, max_digits=19, decimal_places=2)
    count_in_assets = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    is_shared = models.BooleanField(default=False, help_text="Is shared with other person")
    notes = models.CharField(max_length=300, blank=True)
    shared_users = models.ManyToManyField(
        User,
        blank=True,
        related_name="shared_accounts",
        help_text="Users this account is shared with"
    )

    objects = AccountQuerySet.as_manager()

    class Meta:
        ordering = ["-is_default", "id"]
        constraints = [
            UniqueConstraint(
                fields=["user"],
                condition=Q(is_default=True),
                name="only_one_default_account_per_user",
            )
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.user.username})"
