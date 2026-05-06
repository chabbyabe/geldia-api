from __future__ import annotations

from typing import Any

from dj_rest_auth.serializers import (
    UserDetailsSerializer as DjRestAuthUserDetailsSerializer,
)
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .models import Company, User

class UserRegistrationSerializer(serializers.Serializer):
    username = serializers.CharField(
        max_length=40,
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all(), message="This username is already taken.")]
    )
    first_name = serializers.CharField(max_length=255)
    last_name = serializers.CharField(max_length=255)
    email = serializers.EmailField(max_length=255)
    password_1 = serializers.CharField(write_only=True)
    password_2 = serializers.CharField(write_only=True)

    class Meta:
        model = get_user_model
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "password_1",
            "password_2",
        )

    def get_cleaned_data(self) -> dict[str, Any]:
        return {
            "username": self.validated_data.get("username", ""),
            "password_1": self.validated_data.get("password_1", ""),
            "password_2": self.validated_data.get("password_2", ""),
            "email": self.validated_data.get("email", ""),
            "first_name": self.validated_data.get("first_name", ""),
            "last_name": self.validated_data.get("last_name", ""),
        }

    def validate_username(self, username: str) -> str:
        return username.strip().lower()

    def validate_password_1(self, password: str) -> str:
        return password.strip()


    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "A user with this email already exists."
            )
        return value
    
    def validate(self, data):
        if data["password_1"] != data["password_2"]:
            raise serializers.ValidationError({
                "password_2": "The two password fields didn't match."
            })

        try:
            validate_password(data["password_1"])
        except serializers.ValidationError as e:
            raise serializers.ValidationError(list(e.messages))

        return data

    def create(self, validated_data: dict[str, Any]) -> User:
        user_model = get_user_model()
        user = user_model(
            username=validated_data["username"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            email=validated_data.get("email", ""),
            is_active=False,
        )
        user.set_password(validated_data["password_1"])
        user.save()

        return user 

    def to_representation(self, instance: User) -> dict[str, dict[str, Any]]:
        return {
                "user": {
                    "id": instance.id,
                    "username": instance.username,
                    "first_name": instance.first_name,
                    "last_name": instance.last_name,
                    "email": instance.email
                }
        }

        

class UserSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "first_name", "last_name", "username"]
        read_only_fields = ["id", "first_name", "last_name", "username"]


class CompanySerializer(serializers.ModelSerializer):
    created_by = UserSimpleSerializer(read_only=True)
    updated_by = UserSimpleSerializer(read_only=True)
    is_current = serializers.BooleanField(default=False)
    joined_at = serializers.DateTimeField(required=False, allow_null=True)
    resigned_at = serializers.DateTimeField(required=False, allow_null=True)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        request = self.context.get("request")
        user = getattr(request, "user", None)

        name = attrs.get("name")
        is_current = attrs.get("is_current")

        if user and user.is_authenticated:

            # Check duplicate company name
            if name:
                existing = Company.objects.filter(
                    name__iexact=name.strip(),
                    created_by=user,
                )

                if self.instance:
                    existing = existing.exclude(pk=self.instance.pk)

                if existing.exists():
                    raise serializers.ValidationError("Company already exists.")

            # Check existing current company 
            if is_current:
                current_company = Company.objects.filter(
                    created_by=user,
                    is_current=True,
                )

                if self.instance:
                    current_company = current_company.exclude(pk=self.instance.pk)

                if current_company.exists():
                    raise serializers.ValidationError("You already have a current company.")

        return attrs

    class Meta:
        model = Company
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "deleted_at"]
        extra_kwargs = {
            "name": {"validators": []}
        }


class UserDetailsSerializer(DjRestAuthUserDetailsSerializer):
    email = serializers.EmailField(required=False, allow_null=True)
    company = CompanySerializer(read_only=True)
    company_id = serializers.PrimaryKeyRelatedField(
        source="company",
        queryset=Company.objects.all(),
        required=False,
        allow_null=True,
        write_only=True,
    )
    email_verified = serializers.SerializerMethodField()

    def get_email_verified(self, obj: User) -> dict[str, Any] | None:
        return obj.email_verified_at is not None 

    def to_internal_value(self, data: Any) -> dict[str, Any]:
        if isinstance(data, dict) and "company" in data and "company_id" not in data:
            company_value = data.get("company")
            normalized_data = data.copy()

            if isinstance(company_value, dict):
                company_value = company_value.get("id")

            normalized_data["company_id"] = company_value
            data = normalized_data

        return super().to_internal_value(data)

    def update(self, instance, validated_data):
        company = validated_data.pop("company", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if company is not None:
            if instance.company:
                instance.company.is_current = False
                instance.company.save(update_fields=["is_current"])

            instance.company = company
            instance.company.is_current = True
            instance.company.save(update_fields=["is_current"])
        else: 
            instance.company = None

        instance.save()
        return instance

    class Meta:
        model = get_user_model()
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "company",
            "company_id",
            "is_superuser",
            "email_verified",
        )


class EmailVerificationSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=128)


class PasswordChangeRequestSerializer(serializers.Serializer):
    new_password_1 = serializers.CharField(write_only=True)
    new_password_2 = serializers.CharField(write_only=True)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs["new_password_1"] != attrs["new_password_2"]:
            raise serializers.ValidationError(
                {"new_password_2": "The two password fields didn't match."}
            )

        validate_password(attrs["new_password_1"], self.context["request"].user)
        return attrs


class ForgotPasswordRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    new_password_1 = serializers.CharField(write_only=True)
    new_password_2 = serializers.CharField(write_only=True)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs["new_password_1"] != attrs["new_password_2"]:
            raise serializers.ValidationError(
                {"new_password_2": "The two password fields didn't match."}
            )

        try:
            user = User.objects.get(email=attrs["email"])
        except User.DoesNotExist as exc:
            raise serializers.ValidationError(
                {"email": "No user found with this email address."}
            ) from exc

        validate_password(attrs["new_password_1"], user)
        attrs["user"] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    user = UserSimpleSerializer(read_only=True)

    class Meta:
        model = User
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "deleted_at"]
