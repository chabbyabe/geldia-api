from django.conf import settings
from django.db import models
from django.db.models import QuerySet


class ActiveManager(models.Manager["CommonInfo"]):
    """Model manager that retrieves active items

    This class defines a new default query set so the project can always filter data that is active
    """

    def get_queryset(self) -> QuerySet["CommonInfo"]:
        return super().get_queryset().filter(deleted_at__isnull=True)


class CommonInfo(models.Model):
    """CommonInfo model class

    This class is the parent class for all the models
    """
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_created",
        help_text="User who created this object"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_updated",
        help_text="User who last updated this object"
    )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_deleted",
        help_text="User who deleted this object"
    )

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    # This allows me to escape to default django query set if I need it later in the project
    all_objects = models.Manager["CommonInfo"]()

    # for active query set
    objects = ActiveManager()

    class Meta:
        abstract = True
