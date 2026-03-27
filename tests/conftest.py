import pytest
from django.conf import settings
import psycopg2
import pytest


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:

    # Mark integration and functional as okay to have db access
    for item in items:
        path = str(item.fspath)
        if "integration" in path or "functional" in path:
            item.add_marker(pytest.mark.django_db)
            
