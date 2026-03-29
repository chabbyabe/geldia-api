from __future__ import annotations

import json

from django.db.models import Q
from rest_framework.filters import BaseFilterBackend

from ledger.utils import get_date_range


class MUIFilterBackend(BaseFilterBackend):

    def filter_queryset(self, request, queryset, view):
        filter_model = request.query_params.get("filterModel")
        if not filter_model:
            return queryset

        try:
            filter_model = json.loads(filter_model)
        except json.JSONDecodeError:
            return queryset

        # Expecting structure: { "items": [ { "field": "name", "operator": "contains", "value": "Rent" }, ... ] }
        items = filter_model.get("items", [])
        q_objects = Q()

        for item in items:
            field = item.get('field')
            operator = item.get('operator')
            value = item.get('value')

            has_empty_string = field in ["notes"]

            if operator == "isEmpty":
                condition = Q(**{f"{field}__isnull": True})
                
                if has_empty_string:
                    condition |= Q(**{field: ""})

                q_objects &= condition
                continue


            if operator == "isNotEmpty":
                condition = ~Q(**{f"{field}__isnull": True})
                
                if has_empty_string:
                    condition &= ~Q(**{field: ""})

                q_objects &= condition
                continue


            if value in [None, ""]:
                continue

            if operator in ["contains", "startsWith", "endsWith"]:
                lookup = {
                    "contains": "icontains",
                    "startsWith": "istartswith",
                    "endsWith": "iendswith"
                }[operator]
                q_objects &= Q(**{f"{field}__{lookup}": value})

            elif operator in [">", ">=", "<", "<="]:
                lookup = {
                    ">": "gt",
                    ">=": "gte",
                    "<": "lt",
                    "<=": "lte"
                }[operator]
                q_objects &= Q(**{f"{field}__{lookup}": value})

            elif operator == "=":
                q_objects &= Q(**{f"{field}": value})

        queryset = queryset.filter(q_objects)

        filter_date = request.query_params.get("filterBy")
        start_date = request.query_params.get("startDate")
        end_date = request.query_params.get("endDate")

        start_date, end_date = get_date_range(
            request, 
            filter_type=filter_date, 
            start_date=start_date, 
            end_date=end_date
        )

        if start_date and end_date:
            queryset = queryset.filter(transaction_at__date__range=(start_date, end_date))
        elif start_date:
            queryset = queryset.filter(transaction_at__date__gte=start_date)
        elif end_date:
            queryset = queryset.filter(transaction_at__date__lte=end_date)

        return queryset
