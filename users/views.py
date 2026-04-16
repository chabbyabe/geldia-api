from __future__ import annotations

from rest_framework import generics, permissions
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from core.viewsets.mixins import UserAuditMixin
from users.models import User
from users.serializers import UserRegistrationSerializer, UserSimpleSerializer
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from ledger.serializers.categories import CategorySerializer
from ledger.models import Category

class UserRegisterView(generics.CreateAPIView, UserAuditMixin):
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []  # skip JWT auth for registration


class UserViewSet(viewsets.ModelViewSet, UserAuditMixin):
    serializer_class = UserSimpleSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    http_method_names = ['get']

    def get_queryset(self):
        return User.objects.filter(is_superuser=False, deleted_at__isnull=True)


class UserSettingsViewSet(ViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = None

    @action(detail=False, methods=['get'], url_path="categories")
    def user_categories(self, request):
        categories = (
            Category.objects.filter(created_by=request.user)
        )
        return Response(CategorySerializer(categories, many=True).data)