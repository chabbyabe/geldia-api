from django.db import models
from django.db.models import Q, DateField, Sum
from django.db.models.functions import Coalesce, TruncDate

class TransactionQuerySet(models.QuerySet):

    def visible_to(self, user):
        return self._for_user(user)
    
    def _for_user(self, user):
        return self.filter(
            Q(created_by=user) |
            Q(account__user=user),
            deleted_at__isnull=True,
        )

    def for_year(self, year):
        return self.filter(
            Q(transaction_at__year=year) |
            Q(debit_month_year__year=year)
        )

    def with_transaction_date(self):
        return self.annotate(
            transaction_date=Coalesce(
                "debit_month_year",
                TruncDate("transaction_at"),
                output_field=DateField()
            )
        )
    
    def with_amount_totals(self):
        return self.annotate(
            net_amount_total=Sum("net_amount"),
            gross_amount_total=Sum("gross_amount"),
            expenses_amount_total=Sum("amount")
        )
    
    def filter_by_date_range(self, start_date, end_date):
        return self.filter(
            Q(transaction_at__range=[start_date, end_date]) |
            Q(debit_month_year__range=[start_date, end_date])
        )

    def filter_by_transaction_type(self, name):
        return self.filter(
            transaction_type__name=name
        ) 
    
    def by_category_totals(self):
        return (
            self.values(
                "category__name",
                "category__icon",
                "category__color",
                "category__parent_category",
            )
            .annotate(total_amount=Sum("amount"))
            .order_by("-total_amount")
        )