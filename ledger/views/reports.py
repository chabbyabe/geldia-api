from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from ledger.models import Transaction
from django.db.models import F, Sum
from ledger.constants import TxnType
from django.db.models.functions import TruncMonth
import calendar
from ledger.serializers.reports import IncomeReportSerializer

def normalize_category(name):
    if not name:
        return "other"
    return name.strip().lower()

class ReportViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path="income-report")
    def income_report(self, request):
        serializer = IncomeReportSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        selected_year = serializer.get_selected_year()
        compare_year = serializer.get_compare_year()
        years = [selected_year, compare_year]

        # Query all relevant transactions for both years at once
        qs = (
            Transaction.objects
            .visible_to(request.user)
            .filter_by_transaction_type(TxnType.INCOME)
            .with_transaction_date()
            .filter(debit_month_year__year__in=years)
        )

        data = (
            qs.annotate(month=TruncMonth("debit_month_year"))
            .values("month", "store__name")
            .annotate(
                gross_amount=Sum("gross_amount"),
                net_amount=Sum("net_amount")
            )
            .order_by("month")
        )

        # Prepare empty result buckets for both years
        result = {}
        for year in years:
            for m in range(1, 13):
                key = f"{year}-{m:02d}"
                result[key] = {
                    "month": m,
                    "month_label": calendar.month_abbr[m],
                    "gross_amount": 0,
                    "net_amount": 0,
                    "companies": []
                }

        # Populate result
        for row in data:
            month_obj = row["month"]
            key = month_obj.strftime("%Y-%m")
            bucket = result[key]

            gross = row["gross_amount"] or 0
            net = row["net_amount"] or 0

            bucket["gross_amount"] += gross
            bucket["net_amount"] += net

            bucket["companies"].append({
                "name": row["store__name"] or "-",
                "gross_amount": gross,
                "net_amount": net,
            })

        # Split the data by year
        selected_data = [v for k, v in result.items() if k.startswith(str(selected_year))]
        compare_data = [v for k, v in result.items() if k.startswith(str(compare_year))]

        return Response({
            "selected_year": selected_year,
            "compare_year": compare_year,
            "base_data": selected_data,
            "compare_data": compare_year and compare_data,
        }, status=200)