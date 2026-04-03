from __future__ import annotations

import json
from django.db.models import Q
from rest_framework.filters import BaseFilterBackend
from ledger.utils import get_date_range


class MUIBaseFilterBackend(BaseFilterBackend):
    filter_type = None
    date_field = None
    empty_string_fields = []
    json_field = None  # e.g. "new_data"

    def filter_queryset(self, request, queryset, view):
        queryset = self.apply_mui_filters(request, queryset)
        queryset = self.apply_date_filters(request, queryset)
        return queryset

    def normalize_field(self, field: str) -> str:
        """
        Supports:
        - dot notation: new_data.amount
        - django lookup: new_data__amount
        """
        return field.replace(".", "__")

    def apply_mui_filters(self, request, queryset):
        filter_model = request.query_params.get("filterModel")
        if not filter_model:
            return queryset

        try:
            filter_model = json.loads(filter_model)
        except json.JSONDecodeError:
            return queryset

        items = filter_model.get("items", [])
        q_objects = Q()

        for item in items:
            field = item.get("field")
            operator = item.get("operator")
            value = item.get("value")

            if not field or not operator:
                continue

            field = self.normalize_field(field)
            has_empty_string = field in self.empty_string_fields

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

            # skip empty values for normal ops
            if value in [None, ""]:
                continue

            q_objects &= self.build_condition(field, operator, value)

        return queryset.filter(q_objects)


    def build_condition(self, field, operator, value):
        lookup_map = {
            "contains": "icontains",
            "startsWith": "istartswith",
            "endsWith": "iendswith",
        }

        numeric_map = {
            ">": "gt",
            ">=": "gte",
            "<": "lt",
            "<=": "lte",
        }

        if self.json_field and field.startswith(f"{self.json_field}__"):
            django_field = field

            # convert numeric values for JSON
            if operator in numeric_map:
                try:
                    value = float(value) if "." in str(value) else int(value)
                except (TypeError, ValueError):
                    return Q()

                return Q(**{f"{django_field}__{numeric_map[operator]}": value})

            if operator in lookup_map:
                return Q(**{f"{django_field}__{lookup_map[operator]}": value})

            if operator == "=":
                return Q(**{django_field: value})

            if operator == "isEmpty":
                return Q(**{f"{django_field}__isnull": True}) | Q(**{django_field: ""})

            if operator == "isNotEmpty":
                return ~Q(**{f"{django_field}__isnull": True}) & ~Q(**{django_field: ""})

            return Q()

        if operator in numeric_map:
            try:
                value = float(value) if "." in str(value) else int(value)
            except (TypeError, ValueError):
                return Q()

            return Q(**{f"{field}__{numeric_map[operator]}": value})


        if operator in lookup_map:
            return Q(**{f"{field}__{lookup_map[operator]}": value})


        if operator == "=":
            return Q(**{field: value})

        return Q()


    def apply_date_filters(self, request, queryset):
        if not self.date_field:
            return queryset

        filter_date = request.query_params.get("filterBy")
        start_date = request.query_params.get("startDate")
        end_date = request.query_params.get("endDate")

        start_date, end_date = get_date_range(
            request,
            filter_type=filter_date,
            start_date=start_date,
            end_date=end_date,
        )

        if start_date and end_date:
            return queryset.filter(**{
                f"{self.date_field}__date__range": (start_date, end_date)
            })

        if start_date:
            return queryset.filter(**{
                f"{self.date_field}__date__gte": start_date
            })

        if end_date:
            return queryset.filter(**{
                f"{self.date_field}__date__lte": end_date
            })

        return queryset