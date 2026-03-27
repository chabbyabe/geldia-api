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
