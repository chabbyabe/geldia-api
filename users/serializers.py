from __future__ import annotations

from typing import Any

from dj_rest_auth.serializers import (
    UserDetailsSerializer as DjRestAuthUserDetailsSerializer,
)
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .models import User


class UserRegistrationSerializer(serializers.Serializer):
    username = serializers.CharField(
        max_length=40,
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all(), message="This username is already taken.")]
    )
    first_name = serializers.CharField(max_length=255)
    last_name = serializers.CharField(max_length=255)
    password_1 = serializers.CharField(write_only=True)
    password_2 = serializers.CharField(write_only=True)

    class Meta:
        model = get_user_model
        fields = (
            'id',
            "username",
            "first_name",
            "last_name",
            "password_1",
            "password_2",
        )

    def get_cleaned_data(self) -> dict[str, Any]:
        return {
            "username": self.validated_data.get("username", ""),
            "password_1": self.validated_data.get("password_1", ""),
            "password_2": self.validated_data.get("password_2", ""),
            "first_name": self.validated_data.get("first_name", ""),
            "last_name": self.validated_data.get("last_name", ""),
        }

    def validate_username(self, username: str) -> str:
        return username.strip().lower()

    def validate_password_1(self, password: str) -> str:
        return password.strip()

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        if data["password_1"] != data["password_2"]:
            raise serializers.ValidationError(
                {"password_2": "The two password fields didn't match."}
            )
        return data

    def create(self, validated_data: dict[str, Any]) -> User:
        user_model = get_user_model()
        user = user_model(
            username=validated_data["username"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
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
                }
        }


class UserDetailsSerializer(DjRestAuthUserDetailsSerializer):
    """
    User model w/o password
    """

    class Meta:
        extra_fields = []
        # see https://github.com/iMerica/dj-rest-auth/issues/181
        # UserModel.XYZ causing attribute error while importing other
        # classes from `serializers.py`. So, we need to check whether the auth model has
        # the attribute or not
        if hasattr(get_user_model(), "USERNAME_FIELD"):
            extra_fields.append(get_user_model().USERNAME_FIELD)
        if hasattr(get_user_model(), "EMAIL_FIELD"):
            extra_fields.append(get_user_model().EMAIL_FIELD)
        if hasattr(get_user_model(), "first_name"):
            extra_fields.append("first_name")
        if hasattr(get_user_model(), "last_name"):
            extra_fields.append("last_name")
        model = get_user_model()
        fields = ("id", *extra_fields)
        read_only_fields = ("email",)
        

class UserSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "first_name", "last_name", "username"]

class UserSerializer(serializers.ModelSerializer):
    user = UserSimpleSerializer(read_only=True)

    class Meta:
        model = User
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "deleted_at"]
