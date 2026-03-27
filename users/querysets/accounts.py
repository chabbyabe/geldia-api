from django.db import models
from django.db.models import Q
class AccountQuerySet(models.QuerySet):

    def visible_to(self, user):
        return self.for_user(user)
    
    def for_user(self, user):
        return self.filter(
            Q(user=user) |
            Q(shared_users=user),
            deleted_at__isnull=True,
        )
