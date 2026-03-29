from __future__ import annotations

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from core.pagination import CustomPageNumberPagination
from ledger.models import Place
from ledger.serializers.places import PlaceSerializer

class PlaceViewSet(viewsets.ModelViewSet):
    serializer_class = PlaceSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination
    http_method_names = ["get", "post", "patch", "delete"]

    # Get only for the authenticated user's own account
    def get_queryset(self):
        return Place.objects.filter(created_by=self.request.user)

    # Create only for authenticated users
    def perform_create(self, serializer) -> None:
        serializer.save(created_by=self.request.user)
