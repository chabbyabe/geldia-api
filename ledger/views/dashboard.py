from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import F, Sum
import calendar
from rest_framework import status
from rest_framework.exceptions import ValidationError

from ledger.constants import DateRange, TxnType
from ledger.models import Transaction, TransactionType
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
        return Response(TransactionSerializer(transactions, many=True).data)


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

        return Response(serializer.data)


    @action(detail=False, methods=['get'], url_path="summary-overview")
    def summary_overview(self, request):
        income_name = TxnType.INCOME
        expenses_name = TxnType.EXPENSES

        start_date, end_date = get_date_range(request, filter_type=DateRange.YEAR)
        
        types = TransactionType.objects.filter(name__in=[income_name, expenses_name])
        type_map = {t.name: t for t in types}

        income_total = (
            Transaction.objects
                .visible_to(request.user)
                .filter_by_transaction_type(income_name)
                .filter_by_date_range(start_date, end_date)
                .aggregate(net_amount=Sum('net_amount'))
                .get('net_amount') or 0
        )
        
        expenses_total = (
            Transaction.objects
                .visible_to(request.user)
                .filter_by_transaction_type(expenses_name)
                .filter_by_date_range(start_date, end_date)
                .aggregate(amount=Sum('amount'))
                .get('amount') or 0
        )

        # Get account that has `Savings` name to show balance
        savings_balance = (
            Account.objects
                .visible_to(request.user)
                .filter(name="Savings")
                .aggregate(balance=Sum('balance')
            )
        )

        summary_overview = [
            SummaryOverviewSerializer({
                "name": type_map[income_name].name,
                "icon": type_map[income_name].icon,
                "color": type_map[income_name].color,
                "amount": income_total
            }).data,
            SummaryOverviewSerializer({
                "name": type_map[expenses_name].name,
                "icon": type_map[expenses_name].icon,
                "color": type_map[expenses_name].color,
                "amount": expenses_total
            }).data,
            SummaryOverviewSerializer({
                "name": "Savings",
                "icon": "Balance",
                "color": "#F5A524",
                "amount": savings_balance["balance"]
            }).data,
        ]
    
        return Response(summary_overview)


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
            qs = (
                Transaction.objects
                    .visible_to(request.user)
                    .for_year(year)
                    .with_transaction_date()
                    .values("transaction_date", type=F("transaction_type__name"))
                    .with_amount_totals()
                    .order_by("transaction_date", "type")
            )

            for row in qs:
                index = row["transaction_date"].month - 1
                if row["type"] == income_name:
                    income_net_data[index] = float(row["net_amount_total"] or 0)
                    income_gross_data[index] = float(row["gross_amount_total"] or 0)
                else:
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
