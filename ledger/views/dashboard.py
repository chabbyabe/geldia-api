from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Sum
from django.db.models.functions import TruncMonth
import calendar
from rest_framework import status
from rest_framework.exceptions import ValidationError

from ledger.constants import DateRange, TxnType
from ledger.models import Transaction
from ledger.serializers.categories import CategoryOverviewSerializer
from ledger.serializers.dashboard import SummaryOverviewSerializer, YearOverviewQuerySerializer
from ledger.serializers.transactions import TransactionSerializer
from ledger.utils import get_date_range
from users.models import Account

class DashboardViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path="recent-transactions")
    def recent_transactions(self, request):
        transactions = (
            Transaction.objects
            .visible_to(request.user)
            .order_by('-created_at')[:5]
        )
        return Response(TransactionSerializer(transactions, many=True).data, status=status.HTTP_200_OK)


    @action(detail=False, methods=['get'], url_path="category-overview")
    def category_overview(self, request):
        filter_type = request.query_params.get("filterBy")
        start_date = filter_type == DateRange.CUSTOM and request.query_params.get("startDate") 
        end_date = filter_type == DateRange.CUSTOM and request.query_params.get("endDate")

        start_date, end_date = get_date_range(
            request, filter_type=filter_type, start_date=start_date, end_date=end_date
            )

        queryset = (
            Transaction.objects
                .visible_to(request.user)
                .filter_by_transaction_type(TxnType.EXPENSES)
                .filter_by_date_range(start_date, end_date)
            )
        
        categories = (queryset.by_category_totals())

        data = [
            {
                "name": c["category__name"],
                "icon": c["category__icon"],
                "color": c["category__color"],
                "is_parent": c["category__parent_category"] is not None,
                "amount": c["total_amount"],
            }
            for c in categories
        ]

        serializer = CategoryOverviewSerializer(data, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)


    @action(detail=False, methods=["get"], url_path="summary-overview")
    def summary_overview(self, request):
        start_date, end_date = get_date_range(request, filter_type=DateRange.YEAR)

        base_txn_qs = (
            Transaction.objects
            .visible_to(request.user)
            .filter_by_date_range(start_date, end_date)
            .exclude(category__name="Savings")
        )

        income_total = (
            base_txn_qs
            .filter_by_transaction_type(TxnType.INCOME)
            .aggregate(total=Sum("net_amount"))["total"]
            or 0
        )

        expenses_total = (
            base_txn_qs
            .filter_by_transaction_type(TxnType.EXPENSES)
            .aggregate(total=Sum("amount"))["total"]
            or 0
        )

        savings_balance = (
            Account.objects
            .visible_to(request.user)
            .filter(is_savings=True)
            .distinct()
            .aggregate(balance=Sum("balance"))["balance"]
            or 0
        )

        summary_overview : list = [
            {
                "name": TxnType.INCOME,
                "icon": "Savings", 
                "color": "#006CD1",        
                "amount": income_total,
            },
            {
                "name": TxnType.EXPENSES,
                "icon": "Payments",
                "color": "#E5484D",
                "amount": expenses_total,
            },
            {
                "name": "Savings",
                "icon": "Balance",
                "color": "#F5A524",
                "amount": savings_balance,
            },
        ]

        serializer = SummaryOverviewSerializer(summary_overview, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)


    @action(detail=False, methods=['get'], url_path="year-overview")
    def year_overview(self, request):
        income_name = TxnType.INCOME
        expenses_name = TxnType.EXPENSES

        serializer = YearOverviewQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        year = serializer.get_year()

        months = list(calendar.month_abbr)[1:]

        income_net_data = [0] * 12
        income_gross_data = [0] * 12
        expense_data = [0] * 12
        try:
            income_rows = (
                Transaction.objects
                .visible_to(request.user)
                .filter_by_transaction_type(TxnType.INCOME)
                .with_transaction_date()
                .for_year(year)
                .annotate(month=TruncMonth("transaction_date"))
                .values("month")
                .annotate(
                    net_amount_total=Sum("net_amount"),
                    gross_amount_total=Sum("gross_amount"),
                )
                .order_by("month")
            )
            expenses_rows = (
                Transaction.objects
                .visible_to(request.user)
                .filter_by_transaction_type(TxnType.EXPENSES)
                .with_transaction_date()
                .for_year(year)
                .annotate(month=TruncMonth("transaction_date"))
                .values("month")
                .annotate(expenses_amount_total=Sum("amount"))
                .order_by("month")
            )

            for row in income_rows:
                index = row["month"].month - 1
                income_net_data[index] = float(row["net_amount_total"] or 0)
                income_gross_data[index] = float(row["gross_amount_total"] or 0)

            for row in expenses_rows:
                index = row["month"].month - 1
                expense_data[index] = float(row["expenses_amount_total"] or 0)

        except Exception:
            raise ValidationError({"error":"Failed to fetch year overview"})

        data : list = [
            {
                "name": income_name,
                "label": months,
                "data": income_net_data,
                "year": str(year),
                "is_gross": False
            },
            {
                "name": income_name,
                "label": months,
                "data": income_gross_data,
                "year": str(year),
                "is_gross": True
            },
            {
                "name": expenses_name,
                "label": months,
                "data": expense_data,
                "year": str(year)
            }
        ]    
        return Response(data, status=status.HTTP_200_OK)
