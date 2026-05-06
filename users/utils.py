from django.core.mail import send_mail
import secrets
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.utils.http import urlencode

from users.models import EmailVerification, User

def create_email_verification(
    *,
    user: User,
    purpose: str,
    expiry_minutes: int,
    pending_password: str | None = None,
) -> EmailVerification:
    
    EmailVerification.objects.filter(
        user=user,
        purpose=purpose,
        used_at__isnull=True,
    ).delete()

    return EmailVerification.objects.create(
        user=user,
        purpose=purpose,
        token=secrets.token_urlsafe(32),
        pending_password=pending_password,
        expires_at=timezone.now() + timedelta(minutes=expiry_minutes),
    )


def send_verification_email(*, user: User, verification: EmailVerification) -> None:
    if verification.purpose == EmailVerification.Purpose.REGISTRATION:
        verification_url = (
            f"{settings.REGISTRATION_VERIFY_URL}"
            f"?{urlencode({'token': verification.token})}"
        )
        manual_verification_url = settings.REGISTRATION_MANUAL_VERIFY_URL
        subject = "Verify your email"
        body = (
            "Click this link to activate your account:\n\n"
            f"{verification_url}\n\n"
            "If the link does not work, open this manual verification page:\n\n"
            f"{manual_verification_url}\n\n"
            "Then copy and paste this verification token:\n"
            f"{verification.token}\n"
        )
    else:
        verification_url = (
            f"{settings.PASSWORD_CHANGE_VERIFY_URL}"
            f"?{urlencode({'token': verification.token})}"
        )
        manual_verification_url = settings.PASSWORD_CHANGE_MANUAL_VERIFY_URL
        subject = "Verify your password change"
        body = (
            "Click this link to confirm your password change:\n\n"
            f"{verification_url}\n\n"
            "If the link does not work, open this manual verification page:\n\n"
            f"{manual_verification_url}\n\n"
            "Then copy and paste this verification token:\n"
            f"{verification.token}\n"
        )

    send_mail(
        subject,
        body,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )


def verify_token(token: str, purpose: str) -> tuple[bool, str]:

    if purpose == EmailVerification.Purpose.REGISTRATION:
        message = "Email verified successfully."
        is_register = True
    elif purpose == EmailVerification.Purpose.PASSWORD_CHANGE:
        message = "Password changed successfully."
        is_register = False

    verification = (
        EmailVerification.objects
        .filter(
            token=token,
            purpose=purpose,
            used_at__isnull=True,
        )
        .select_related("user")
        .first()
    )

    if not verification or verification.expires_at <= timezone.now():
        return False, "Invalid or expired verification token."

    user = verification.user

    if is_register:
        user.is_active = True
        user.email_verified_at = timezone.now()
        user.save(update_fields=["is_active", "email_verified_at"])
    else:
        user.password = verification.pending_password
        user.save(update_fields=["password"])

    verification.used_at = timezone.now()
    verification.save(update_fields=["used_at"])

    return True, message
