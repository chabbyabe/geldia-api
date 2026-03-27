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
        return self.post(login_url, login_data)
