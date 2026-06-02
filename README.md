# Overview

The system will allow users to record income, expenses, and savings, categorize transactions, generate reports, and monitor financial trends over time. 

# Setup

### Django

Python Version: 3.10

#### Install dependencies with Poetry

```bash
$ poetry install
```

```bash
$ python -m pip install --upgrade packaging
```

#### Setup .env

##### Create ".env" file on root project and fill it up

There should be a sample called .env.sample to base on

### Production email checklist

For registration emails to work in production, make sure these values are set:

```bash
DJANGO_ENVIRONMENT_SETTINGS=prod
DEBUG=False
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=your-smtp-host
EMAIL_PORT=587
EMAIL_HOST_USER=your-smtp-username
EMAIL_HOST_PASSWORD=your-smtp-password
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
DEFAULT_FROM_EMAIL=noreply@your-domain.com
API_BASE_URL=https://api.your-domain.com
APP_URL=https://your-frontend-domain.com/login
```

If `DJANGO_ENVIRONMENT_SETTINGS` is left as `dev`, Django will use development behavior and emails may be written to logs instead of being sent.

If `EMAIL_HOST` is not set in production, this project falls back to `localhost`, which usually does not work unless the server is running its own SMTP service.

#### Migrate migrations

```bash
$ poetry run python manage.py migrate
```

#### Run the development server

```bash
$ poetry run python manage.py runserver
```

#### Run tests

```bash
$ poetry run pytest
```
