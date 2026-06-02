from django.core.exceptions import ImproperlyConfigured
from .core.settings.base import *


DEBUG = False


def _validate_production_email_settings() -> None:
    if EMAIL_BACKEND != "django.core.mail.backends.smtp.EmailBackend":
        return

    if EMAIL_HOST == "localhost":
        raise ImproperlyConfigured(
            "Production email is configured for SMTP, but EMAIL_HOST is still "
            "'localhost'. Set your real SMTP host in the production env."
        )

    if DEFAULT_FROM_EMAIL.endswith(".local"):
        raise ImproperlyConfigured(
            "Production email is configured for SMTP, but DEFAULT_FROM_EMAIL is "
            "still using the local placeholder value. Set a real sender address."
        )


_validate_production_email_settings()
