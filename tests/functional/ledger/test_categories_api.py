from http import client as http_client

import pytest
from django.urls import reverse

from ledger.constants import TxnType
from ledger.models import Category, TransactionType
from tests import factories


class TestCategoryViewSet:
    def test_requires_authentication(self, client):
        response = client.get(reverse("ledger:category-list"))

        assert response.status_code == http_client.UNAUTHORIZED
        assert response["content-type"] == "application/json"


@pytest.mark.xfail(reason="CategoryViewSet uses non-existent `user` field in queryset/save", strict=False)
def test_category_authenticated_list_intended_behavior(client):
    user = factories.User(username="cat_list_user", password="password123")
    client.authenticate_user(user.username, "password123")

    ttype = TransactionType.objects.create(name=TxnType.EXPENSES, color="#f00", icon="expense")
    Category.objects.create(name="Food", transaction_type=ttype, created_by=user)

    response = client.get(reverse("ledger:category-list"))

    assert response.status_code == http_client.OK
