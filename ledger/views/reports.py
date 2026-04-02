from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from ledger.models import Transaction
from django.db.models import F, Sum
from ledger.constants import TxnType, MONTHS
from django.db.models.functions import TruncMonth
import calendar
from ledger.serializers.reports import ReportParamRequestSerializer, \
    IncomeReportResponseSerializer, ExpensesReportSerializer

def normalize_category(name):
    if not name:
        return "other"
    return name.strip().lower()

class ReportViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

def normalize_category(name):
    if not name:
        return "other"
    return name.strip().lower()

class ReportViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path="income-report")
    def income_report(self, request):
        serializer = ReportParamRequestSerializer(data=request.query_params)
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

        response_data = {
            "selected_year": selected_year,
            "compare_year": compare_year,
            "base_data": selected_data,
            "compare_data": compare_year and compare_data,
        }

        serializer = IncomeReportResponseSerializer(response_data)
        return Response(serializer.data, status=200)

    @action(detail=False, methods=['get'], url_path="expenses-report")
    def expenses_report(self, request):
        serializer = ReportParamRequestSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        selected_year = serializer.get_selected_year()
        compare_year = serializer.get_compare_year()
        years = [selected_year, compare_year]

        qs = (
            Transaction.objects
            .visible_to(request.user)
            .filter_by_transaction_type(TxnType.EXPENSES)
            .with_transaction_date()
            .filter(transaction_date__year__in=years)
        )

        data = (
            qs.annotate(date=TruncMonth("transaction_date"))
            .values("date", "category__name")
            .annotate(total=Sum("amount"))
            .order_by("date")
        )

        def init_result():
            return {
                month_num: {
                    "month": month_num,
                    "date": month_name,
                    "categories": {},
                    "total": 0
                }
                for month_num, month_name in MONTHS.items()
            }

        base_result = init_result()
        compare_result = init_result() if compare_year else None

        for row in data:
            month_num = row["date"].month
            year = row["date"].year
            raw_category = row["category__name"]
            category = normalize_category(raw_category).title()
            total = row["total"] or 0

            # choose correct bucket
            if year == selected_year:
                target = base_result
            elif compare_year and year == compare_year:
                target = compare_result
            else:
                continue

            month_data = target[month_num]
            month_data["categories"].setdefault(category, 0)
            month_data["categories"][category] += total
            month_data["total"] += total

        base_data = sorted(base_result.values(), key=lambda x: x["month"])

        compare_data = (
            sorted(compare_result.values(), key=lambda x: x["month"])
            if compare_result else None
        )

        return Response({
            "selected_year": selected_year,
            "compare_year": compare_year,
            "base_data": ExpensesReportSerializer(base_data, many=True).data,
            "compare_data": ExpensesReportSerializer(compare_data, many=True).data if compare_data else None,
        }, status=200)

