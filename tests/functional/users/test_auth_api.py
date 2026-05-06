from http import client as http_client
from urllib.parse import parse_qs, urlparse
from django.core import mail
from django.utils import timezone
from django.urls import reverse
import pytest
from tests import factories
from users.models import Company, EmailVerification


class TestDJRestAuthIntegration:
    def _token_from_last_email(self) -> str:
        body = mail.outbox[-1].body.strip().splitlines()
        return body[-1].strip()

    def _verification_link_from_last_email(self) -> str:
        body = mail.outbox[-1].body.strip().splitlines()
        return body[2].strip()

    def _manual_verification_link_from_last_email(self) -> str:
        body = mail.outbox[-1].body.strip().splitlines()
        return body[6].strip()

    def _password_change_manual_verification_link_from_last_email(self) -> str:
        body = mail.outbox[-1].body.strip().splitlines()
        return body[6].strip()

    def test_login_success(self, client):
        """
        Given: An existing user tries to login with valid details
        Expect: That we can login properly
        """

        # Arrange
        # Create a new user
        username = "johndoe"
        password = "password"
        user = factories.User(username=username, password=password)

        # Prepare the data for login
        url = reverse("rest_login")
        login_data = {
            "username": username,
            "password": password,
        }

        # Act
        response = client.post(url, login_data)

        # Assert
        assert response.status_code == http_client.OK
        assert response["content-type"] == "application/json"
        assert "access" in response.data
        assert "refresh" in response.data
        assert "user" in response.data
        assert response.data["user"]["username"] == user.username

    def test_login_fails(self, client):
        """
        Given: An existing user tries to login with invalid detail
        Expect: The existing user fails to login
        """

        # Arrange
        # Create a new user
        username = "johndoe"
        wrong_password = "wrong password"
        right_password = "right password"
        factories.User(username=username, password=right_password)

        # Prepare data for login
        url = reverse("rest_login")
        login_data = {
            "username": username,
            "password": wrong_password,
        }

        # Act
        response = client.post(url, login_data)

        # Assert
        assert response.status_code == http_client.BAD_REQUEST
        assert response["content-type"] == "application/json"

    def test_register_sends_verification_email_and_creates_inactive_user(self, client):
        response = client.post(
            reverse("rest_register"),
            {
                "username": "verifyme",
                "first_name": "Verify",
                "last_name": "Me",
                "email": "verify@example.com",
                "password_1": "StrongPassword123!",
                "password_2": "StrongPassword123!",
            },
            format="json",
        )

        assert response.status_code == http_client.CREATED
        assert response.data["detail"] == "Registration successful. Verify your email to activate your account."
        assert len(mail.outbox) == 1
        verification_link = self._verification_link_from_last_email()
        manual_verification_link = self._manual_verification_link_from_last_email()
        parsed_link = urlparse(verification_link)
        manual_parsed_link = urlparse(manual_verification_link)

        assert parsed_link.path == "/api/users/auth/register/verify/"
        assert manual_parsed_link.path == "/api/users/auth/email/manual-verify/"
        assert parse_qs(parsed_link.query)["token"]

        user = factories.User._meta.model.objects.get(username="verifyme")
        assert user.is_active is False
        assert user.email_verified_at is None
        assert EmailVerification.objects.filter(
            user=user,
            purpose=EmailVerification.Purpose.REGISTRATION,
            used_at__isnull=True,
        ).exists()

    def test_register_verify_activates_user_and_allows_login(self, client):
        client.post(
            reverse("rest_register"),
            {
                "username": "verifieduser",
                "first_name": "Verified",
                "last_name": "User",
                "email": "verified@example.com",
                "password_1": "StrongPassword123!",
                "password_2": "StrongPassword123!",
            },
            format="json",
        )
        token = self._token_from_last_email()

        response = client.post(
            reverse("rest_register_verify"),
            {"token": token},
            format="json",
        )

        assert response.status_code == http_client.OK
        assert response.data["detail"] == "Email verified successfully."

        user = factories.User._meta.model.objects.get(username="verifieduser")
        assert user.is_active is True
        assert user.email_verified_at is not None

        login_response = client.authenticate_user("verifieduser", "StrongPassword123!")
        assert login_response.status_code == http_client.OK

    def test_register_verify_link_activates_user(self, client):
        client.post(
            reverse("rest_register"),
            {
                "username": "linkeduser",
                "first_name": "Linked",
                "last_name": "User",
                "email": "linked@example.com",
                "password_1": "StrongPassword123!",
                "password_2": "StrongPassword123!",
            },
            format="json",
        )

        verification_link = self._verification_link_from_last_email()
        parsed_link = urlparse(verification_link)
        response = client.get(
            parsed_link.path,
            parse_qs(parsed_link.query),
        )

        assert response.status_code == http_client.OK
        assert response["content-type"].startswith("text/html")
        assert "Your account is verified." in response.content.decode()
        assert "Email verified successfully." in response.content.decode()
        assert "Open Geldia Web" in response.content.decode()

        user = factories.User._meta.model.objects.get(username="linkeduser")
        assert user.is_active is True
        assert user.email_verified_at is not None

    def test_email_manual_verify_page_renders_manual_form(self, client):
        response = client.get(reverse("rest_email_manual_verify"))

        assert response.status_code == http_client.OK
        assert response["content-type"].startswith("text/html")
        assert "Enter your verification token." in response.content.decode()
        assert 'name="token"' in response.content.decode()
        assert "Open Geldia Web" in response.content.decode()

    def test_register_verify_link_with_invalid_token_renders_error_page(self, client):
        response = client.get(
            reverse("rest_register_verify"),
            {"token": "invalid-token"},
        )

        assert response.status_code == http_client.BAD_REQUEST
        assert response["content-type"].startswith("text/html")
        assert "Verification Failed" in response.content.decode()
        assert "Invalid or expired verification token." in response.content.decode()

    def test_email_manual_verify_page_redirects_token_submission(self, client):
        client.post(
            reverse("rest_register"),
            {
                "username": "manualverifyuser",
                "first_name": "Manual",
                "last_name": "Verify",
                "email": "manualverify@example.com",
                "password_1": "StrongPassword123!",
                "password_2": "StrongPassword123!",
            },
            format="json",
        )
        token = self._token_from_last_email()

        response = client.get(
            reverse("rest_email_manual_verify"),
            {"token": token},
        )

        assert response.status_code == http_client.FOUND
        assert response["Location"].endswith(f"/api/users/auth/register/verify/?token={token}")

    def test_register_rolls_back_when_email_send_fails(self, client, monkeypatch):
        def failing_send_mail(*args, **kwargs):
            raise RuntimeError("SMTP unavailable")

        monkeypatch.setattr("users.utils.send_mail", failing_send_mail)

        with pytest.raises(RuntimeError, match="SMTP unavailable"):
            client.post(
                reverse("rest_register"),
                {
                    "username": "mailfailure",
                    "first_name": "Mail",
                    "last_name": "Failure",
                    "email": "mailfailure@example.com",
                    "password_1": "StrongPassword123!",
                    "password_2": "StrongPassword123!",
                },
                format="json",
            )

        assert not factories.User._meta.model.objects.filter(username="mailfailure").exists()
        assert not EmailVerification.objects.filter(
            user__username="mailfailure",
            purpose=EmailVerification.Purpose.REGISTRATION,
        ).exists()

    def test_get_user_details_success(self, client):
        """
        Given: A currently logged-in user tries to get their account info
        Expect: A JSON response containing the user's account info
        """

        # Arrange
        # Create and authenticate user
        username = "justarandomusername"
        password = "password"
        user = factories.User(
            username=username,
            password=password,
        )
        client.authenticate_user(username, password)

        url = reverse("rest_user_details")

        # Act
        response = client.get(url)

        # Assert
        assert response.status_code == http_client.OK
        assert response["content-type"] == "application/json"
        assert response.data["first_name"] == user.first_name
        assert response.data["last_name"] == user.last_name
        assert response.data["username"] == user.username
        assert response.data["email"] == user.email
        assert response.data["company"] is None

    def test_update_user_details_sets_company_by_id(self, client):
        password = "password"
        company = Company.objects.create(name="Acme Inc")
        user = factories.User(password=password, company=None)
        client.authenticate_user(user.username, password)

        url = reverse("rest_user_details")
        response = client.patch(
            url,
            {"company_id": company.id, "email": "updated@example.com"},
            format="json",
        )

        user.refresh_from_db()

        assert response.status_code == http_client.OK
        assert user.email == "updated@example.com"
        assert user.company is not None
        assert user.company.name == "Acme Inc"
        assert user.company_id == company.id
        assert response.data["company"]["name"] == "Acme Inc"
        assert "company_id" not in response.data
        assert response.data["email"] == "updated@example.com"

    def test_update_user_details_changes_company_by_id(self, client):
        password = "password"
        company = Company.objects.create(name="Old Co")
        replacement_company = Company.objects.create(name="New Co")
        user = factories.User(password=password, company=company)
        client.authenticate_user(user.username, password)

        url = reverse("rest_user_details")
        response = client.patch(
            url,
            {"company_id": replacement_company.id},
            format="json",
        )

        user.refresh_from_db()

        assert response.status_code == http_client.OK
        assert user.company_id == replacement_company.id
        assert response.data["company"]["id"] == replacement_company.id
        assert response.data["company"]["name"] == "New Co"

    def test_update_user_details_accepts_company_object_with_id(self, client):
        password = "password"
        company = Company.objects.create(name="Acme Inc")
        user = factories.User(password=password, company=None)
        client.authenticate_user(user.username, password)

        url = reverse("rest_user_details")
        response = client.patch(
            url,
            {"company": {"id": company.id}},
            format="json",
        )

        user.refresh_from_db()

        assert response.status_code == http_client.OK
        assert user.company_id == company.id
        assert response.data["company"]["id"] == company.id
        assert response.data["company"]["name"] == "Acme Inc"

    def test_get_user_details_when_unauthorized_fails(self, client):
        """
        Given: An unauthorized user tries to get their account info
        Expect: An unauthorized error
        """

        # Arrange
        url = reverse("rest_user_details")

        # Act
        response = client.get(url)

        # Assert
        assert response.status_code == http_client.UNAUTHORIZED
        assert response["content-type"] == "application/json"

    def test_logout_success(self, client):
        """
        Given: A currently logged-in user tries to log-out
        Expect: User to be successfully logged out
        """

        # Arrange
        # Create and authenticate user
        username = "johndoe"
        password = "password"
        factories.User(username=username, password=password)
        client.authenticate_user(username, password)

        logout_url = reverse("rest_logout")

        # Act
        response = client.post(logout_url)

        # Assert
        assert response.status_code == http_client.OK
        assert response["content-type"] == "application/json"
        assert response.data["detail"] == "Successfully logged out."

        # Checking if the user is really logged out
        url = reverse("rest_user_details")
        response = client.get(url)
        assert response.status_code == http_client.UNAUTHORIZED

    def test_change_password_success(self, client):
        password = "currentP@ssword"
        user = factories.User(password=password, email_verified_at=timezone.now())
        client.authenticate_user(user.username, password)

        url = reverse("rest_password_change")
        data = {"new_password1": "newP@ssW0rd!123", "new_password2": "newP@ssW0rd!123"}

        response = client.post(url, data)

        assert response.status_code == http_client.OK
        assert response.data["detail"] == "Password changed successfully."
        assert len(mail.outbox) == 0

        client.credentials()
        old_login = client.authenticate_user(user.username, password)
        assert old_login.status_code == http_client.BAD_REQUEST

        new_login = client.authenticate_user(user.username, "newP@ssW0rd!123")
        assert new_login.status_code == http_client.OK

    def test_forgot_password_verify_link_updates_password(self, client):
        password = "currentP@ssword"
        user = factories.User(password=password, email_verified_at=timezone.now())

        client.post(
            reverse("rest_password_forgot"),
            {
                "email": user.email,
                "new_password1": "newP@ssW0rd!123",
                "new_password2": "newP@ssW0rd!123",
            },
        )

        verification_link = self._verification_link_from_last_email()
        parsed_link = urlparse(verification_link)
        response = client.get(parsed_link.path, parse_qs(parsed_link.query))

        assert response.status_code == http_client.OK
        assert response["content-type"].startswith("text/html")
        assert "Your password was updated." in response.content.decode()
        assert "Password changed successfully." in response.content.decode()

        client.credentials()
        old_login = client.authenticate_user(user.username, password)
        assert old_login.status_code == http_client.BAD_REQUEST

        new_login = client.authenticate_user(user.username, "newP@ssW0rd!123")
        assert new_login.status_code == http_client.OK

    def test_password_change_verify_page_without_token_redirects_to_manual_page(self, client):
        response = client.get(reverse("rest_password_change_verify"))

        assert response.status_code == http_client.FOUND
        assert response["Location"].endswith("/api/users/auth/password/change/manual-verify/")

    def test_password_change_manual_verify_page_renders_manual_form(self, client):
        response = client.get(reverse("rest_password_change_manual_verify"))

        assert response.status_code == http_client.OK
        assert response["content-type"].startswith("text/html")
        assert "Enter your verification token." in response.content.decode()
        assert 'name="token"' in response.content.decode()

    def test_password_change_verify_link_with_invalid_token_renders_error_page(self, client):
        response = client.get(
            reverse("rest_password_change_verify"),
            {"token": "invalid-token"},
        )

        assert response.status_code == http_client.BAD_REQUEST
        assert response["content-type"].startswith("text/html")
        assert "Verification Failed" in response.content.decode()
        assert "Invalid or expired verification token." in response.content.decode()

    def test_forgot_password_email_contains_manual_verification_page(self, client):
        password = "currentP@ssword"
        user = factories.User(password=password, email_verified_at=timezone.now())

        response = client.post(
            reverse("rest_password_forgot"),
            {
                "email": user.email,
                "new_password1": "newP@ssW0rd!123",
                "new_password2": "newP@ssW0rd!123",
            },
        )

        manual_verification_link = self._password_change_manual_verification_link_from_last_email()
        parsed_link = urlparse(manual_verification_link)

        assert response.status_code == http_client.OK
        assert response.data["detail"] == "Password reset verification email sent."
        assert parsed_link.path == "/api/users/auth/password/change/manual-verify/"

    def test_password_change_manual_verify_page_redirects_token_submission(self, client):
        password = "currentP@ssword"
        user = factories.User(password=password, email_verified_at=timezone.now())

        client.post(
            reverse("rest_password_forgot"),
            {
                "email": user.email,
                "new_password1": "newP@ssW0rd!123",
                "new_password2": "newP@ssW0rd!123",
            },
        )
        token = self._token_from_last_email()

        response = client.get(
            reverse("rest_password_change_manual_verify"),
            {"token": token},
        )

        assert response.status_code == http_client.FOUND
        assert response["Location"].endswith(f"/api/users/auth/password/change/verify/?token={token}")

    def test_forgot_password_fails_for_unknown_email(self, client):
        response = client.post(
            reverse("rest_password_forgot"),
            {
                "email": "missing@example.com",
                "new_password1": "newP@ssW0rd!123",
                "new_password2": "newP@ssW0rd!123",
            },
        )

        assert response.status_code == http_client.BAD_REQUEST
        assert response.data["email"] == ["No user found with this email address."]

    def test_change_password_fails(self, client):
        password = "P@s$W0rd!"
        user = factories.User(password=password, email_verified_at=timezone.now())
        auth_response = client.authenticate_user(user.username, password)
        access_token = auth_response.data["access"]

        url = reverse("rest_password_change")

        data = {
            "new_password1": "newP@ssW0rd!123",
            "new_password2": "newP@ssW0rd!1235678",
        }

        response = client.post(url, data)
        client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)

        assert response.status_code == http_client.BAD_REQUEST
        assert response["content-type"] == "application/json"

    def test_password_change_verify_with_invalid_token_fails(self, client):
        password = "P@s$W0rd!"
        user = factories.User(password=password, email_verified_at=timezone.now())
        client.authenticate_user(user.username, password)

        response = client.post(
            reverse("rest_password_change_verify"),
            {"token": "invalid-token"},
            format="json",
        )

        assert response.status_code == http_client.BAD_REQUEST
        assert response.data["detail"] == "Invalid or expired verification token."

    def test_token_verify_success(self, client):
        """
        Given: A currently logged-in user tries to check if their valid token is valid
        Expect: An OK response that means the token is valid
        """

        # Arrange
        username = "johndoe"
        password = "password"
        factories.User(username=username, password=password)

        # Get the access token from the user response
        response = client.authenticate_user(username, password)
        token = response.data["access"]
        data = {"token": token}

        url = reverse("token_verify")

        # Act
        response = client.post(url, data)

        # Assert
        assert response.status_code == http_client.OK
        assert response["content-type"] == "application/json"

    def test_token_verify_fails(self, client):
        """
        Given: A logged-in user tries to check if their expired token is valid
        Expect: An unauthorized response that means the token is invalid
        """

        # Arrange
        # Create and authenticate user
        password = "p@$$W0rd"
        user = factories.User(password=password)
        client.authenticate_user(user.username, password)

        url = reverse("token_verify")

        data = {
            "token": "this_is_a_wrong_token",
        }
        # Act
        response = client.post(url, data)

        # Assert
        assert response.status_code == http_client.UNAUTHORIZED
        assert response["content-type"] == "application/json"
