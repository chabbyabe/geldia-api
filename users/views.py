from __future__ import annotations


from django.conf import settings
from django.db import transaction
from django.http import HttpRequest
from django.shortcuts import redirect
from django.shortcuts import render
from django.utils.http import urlencode
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet
from ledger.serializers.categories import CategorySerializer
from ledger.models import Category
from users.utils import create_email_verification, send_verification_email, \
    verify_token

from core.viewsets.mixins import UserAuditMixin
from users.models import Company, EmailVerification, User
from users.serializers import (
    CompanySerializer,
    EmailVerificationSerializer,
    ForgotPasswordRequestSerializer,
    PasswordChangeRequestSerializer,
    UserRegistrationSerializer,
    UserSimpleSerializer,
)
from utils.seeding.categories import seed_categories_for_user

class UserSettingsViewSet(ViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = None

    @action(detail=False, methods=['get'], url_path="categories")
    def user_categories(self, request):
        categories = (
            Category.objects.filter(created_by=request.user)
            .order_by("parent_category_id", "name")
        )
        return Response(CategorySerializer(categories, many=True).data)

class UserRegisterView(generics.CreateAPIView, UserAuditMixin):
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def create(self, request, *args, **kwargs):
        with transaction.atomic():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()

            verification = create_email_verification(
                user=user,
                purpose=EmailVerification.Purpose.REGISTRATION,
                expiry_minutes=60 * 24,
            )
            send_verification_email(user=user, verification=verification)

        return Response(
            {
                "detail": "Registration successful. Verify your email to activate your account.",
                "user": UserRegistrationSerializer(user).data["user"],
            },
            status=status.HTTP_201_CREATED,
        )


class VerifyRegistrationView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request: HttpRequest):
        token = request.query_params.get("token", "").strip()
        if not token:
            return redirect("rest_email_manual_verify")

        serializer = EmailVerificationSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        is_verified, detail = verify_token(serializer.validated_data["token"], 
                                           EmailVerification.Purpose.REGISTRATION)
        state = "success" if is_verified else "error"

        # Seed user categories after email verification
        if is_verified:
            user = EmailVerification.objects.get(token=serializer.validated_data["token"]).user
            seed_categories_for_user(user.id)

        return render(
            request,
            "email_verification_result.html",
            {
                "is_verified": is_verified,
                "detail": detail,
                "state": state,
                "app_url": settings.APP_URL,
                "manual_verify_url": settings.REGISTRATION_MANUAL_VERIFY_URL,
            },
            status=status.HTTP_200_OK if is_verified else status.HTTP_400_BAD_REQUEST,
        )

    def post(self, request):
        serializer = EmailVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        is_verified, detail = verify_token(serializer.validated_data["token"], 
                                           EmailVerification.Purpose.REGISTRATION)
            
        return Response(
            {"detail": detail},
            status=status.HTTP_200_OK if is_verified else status.HTTP_400_BAD_REQUEST,
        )


class ManualRegistrationVerificationView(VerifyRegistrationView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request: HttpRequest):
        token = request.query_params.get("token", "").strip()

        if token:
            return redirect(f"{settings.REGISTRATION_VERIFY_URL}?{urlencode({'token': token})}")

        return render(
            request,
            "email_manual_verification.html",
            {
                "app_url": settings.APP_URL,
            },
            status=status.HTTP_200_OK,
        )


class PasswordChangeRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeRequestSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.set_password(serializer.validated_data["new_password_1"])
        user.save(update_fields=["password"])

        return Response(
            {"detail": "Password changed successfully."},
            status=status.HTTP_200_OK,
        )


class ForgotPasswordRequestView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        with transaction.atomic():
            serializer = ForgotPasswordRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            user = serializer.validated_data["user"]
            user.set_password(serializer.validated_data["new_password_1"])
            verification = create_email_verification(
                user=user,
                purpose=EmailVerification.Purpose.PASSWORD_CHANGE,
                expiry_minutes=15,
                pending_password=user.password,
            )
            send_verification_email(user=user, verification=verification)

        return Response(
            {"detail": "Password reset verification email sent."},
            status=status.HTTP_200_OK,
        )


class VerifyPasswordChangeView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request: HttpRequest):
        token = request.query_params.get("token", "").strip()
        if not token:
            return redirect("rest_password_change_manual_verify")

        serializer = EmailVerificationSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        is_verified, detail = verify_token(serializer.validated_data["token"], 
                                           EmailVerification.Purpose.PASSWORD_CHANGE)
        state = "success" if is_verified else "error"

        return render(
            request,
            "password_change_verification_result.html",
            {
                "is_verified": is_verified,
                "detail": detail,
                "state": state,
                "app_url": settings.APP_URL,
                "manual_verify_url": settings.PASSWORD_CHANGE_MANUAL_VERIFY_URL,
            },
            status=status.HTTP_200_OK if is_verified else status.HTTP_400_BAD_REQUEST,
        )

    def post(self, request):
        serializer = EmailVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        is_verified, detail = verify_token(serializer.validated_data["token"],
                                           EmailVerification.Purpose.PASSWORD_CHANGE)
        return Response(
            {"detail": detail},
            status=status.HTTP_200_OK if is_verified else status.HTTP_400_BAD_REQUEST,
        )


class ManualPasswordChangeVerificationView(VerifyPasswordChangeView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request: HttpRequest):
        token = request.query_params.get("token", "").strip()

        if token:
            return redirect(f"{settings.PASSWORD_CHANGE_VERIFY_URL}?{urlencode({'token': token})}")

        return render(
            request,
            "password_change_manual_verification.html",
            {
                "app_url": settings.APP_URL,
            },
            status=status.HTTP_200_OK,
        )

class UserViewSet(viewsets.ModelViewSet, UserAuditMixin):
    serializer_class = UserSimpleSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    http_method_names = ["get", "post", "patch"]

    def get_queryset(self):
        return User.objects.filter(is_superuser=False, deleted_at__isnull=True)

class CompanyViewSet(UserAuditMixin, viewsets.ModelViewSet):
    serializer_class = CompanySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    http_method_names = ["get", "post", "patch", "delete"]

    def get_queryset(self):
        return (
            Company.objects
            .filter(created_by=self.request.user, deleted_at__isnull=True)
            .order_by("name")
        )

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)