from __future__ import annotations

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from core.pagination import CustomPageNumberPagination
from core.viewsets.mixins import UserAuditMixin
from ledger.models import Place
from ledger.serializers.places import PlaceSerializer

class PlaceViewSet(UserAuditMixin, viewsets.ModelViewSet):
    serializer_class = PlaceSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination
    http_method_names = ["get", "post", "patch", "delete"]

    def get_queryset(self):
        return Place.objects.filter(created_by=self.request.user)
