from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.test import APIClient


@pytest.fixture
def client() -> "JWTAPIClient":
    return JWTAPIClient()


class JWTAPIClient(APIClient):

    def authenticate_user(self, username: str, password: str) -> Response:
        login_url = reverse("rest_login")

        login_data = {
            "username": username,
            "password": password,
        }

        # Login using JWT because the client's force_authenticate function doesn't log out the user
        response = self.post(login_url, login_data, format="json")
        if response.status_code < 400 and isinstance(getattr(response, "data", None), dict):
            access_token = response.data.get("access")
            if access_token:
                self.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        return response

    def post(self, path, data=None, format=None, content_type=None, follow=False, **extra):
        response = super().post(
            path,
            data=data,
            format=format,
            content_type=content_type,
            follow=follow,
            **extra,
        )

        # With header-based JWT auth, "logout" is effectively client-side: drop the token.
        if path == reverse("rest_logout") and response.status_code < 400:
            self.credentials()

        return response
