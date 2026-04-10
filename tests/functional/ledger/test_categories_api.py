from http import client as http_client

from django.urls import reverse

from ledger.constants import TxnType
from ledger.models import Category, TransactionType
from tests import factories


class TestCategoryViewSet:
    def _auth(self, client, username="category_user", password="password123"):
        user = factories.User(username=username, password=password)
        client.authenticate_user(username, password)
        return user

    def _txn_type(self, name=TxnType.EXPENSES):
        return TransactionType.objects.create(name=name, color="#111111", icon="icon")

    def test_requires_authentication(self, client):
        response = client.get(reverse("ledger:category-list"))

        assert response.status_code == http_client.UNAUTHORIZED
        assert response["content-type"] == "application/json"

    def test_list_returns_only_current_users_categories(self, client):
        user = self._auth(client)
        other = factories.User(username="category_other", password="password123")
        expense_type = self._txn_type()
        parent = Category.objects.create(name="Food", transaction_type=expense_type, created_by=user)
        Category.objects.create(
            name="Snacks",
            transaction_type=expense_type,
            parent_category=parent,
            created_by=user,
        )
        Category.objects.create(name="Standalone", transaction_type=expense_type, created_by=user)
        other_parent = Category.objects.create(name="Hidden", transaction_type=expense_type, created_by=other)
        Category.objects.create(
            name="Hidden Child",
            transaction_type=expense_type,
            parent_category=other_parent,
            created_by=other,
        )

        response = client.get(reverse("ledger:category-list"))

        assert response.status_code == http_client.OK
        assert [item["name"] for item in response.data["results"]] == ["Standalone", "Food"]
        assert response.data["results"][0]["children"] == []
        assert response.data["results"][1]["children"] == [
            {
                "id": response.data["results"][1]["children"][0]["id"],
                "name": "Snacks",
                "color": None,
                "icon": None,
                "transaction_type": {
                    "id": expense_type.id,  
                    "name": expense_type.name,
                    "color": expense_type.color,
                    "icon": expense_type.icon,
                },
                "parent_category": {
                    "id": parent.id,
                    "name": "Food",
                    "color": None,
                    "icon": None,
                },
            }
        ]

    def test_create_sets_created_by_to_authenticated_user(self, client):
        user = self._auth(client, username="category_create")
        expense_type = self._txn_type()

        response = client.post(
            reverse("ledger:category-list"),
            {"name": "Rent", "transaction_type_id": expense_type.id, "color": "#123456", "icon": "home"},
            format="json",
        )

        assert response.status_code == http_client.CREATED
        created = Category.objects.get(pk=response.data["id"])
        assert created.created_by_id == user.id
        assert created.transaction_type_id == expense_type.id
        assert response.data["name"] == "Rent"

    def test_retrieve_returns_own_category(self, client):
        user = self._auth(client, username="category_retrieve")
        expense_type = self._txn_type()
        category = Category.objects.create(
            name="Utilities",
            transaction_type=expense_type,
            created_by=user,
        )

        response = client.get(reverse("ledger:category-detail", args=[category.id]))

        assert response.status_code == http_client.OK
        assert response.data["id"] == category.id
        assert response.data["name"] == "Utilities"

    def test_patch_updates_own_category(self, client):
        user = self._auth(client, username="category_patch")
        expense_type = self._txn_type()
        category = Category.objects.create(
            name="Bills",
            transaction_type=expense_type,
            created_by=user,
        )

        response = client.patch(
            reverse("ledger:category-detail", args=[category.id]),
            {"name": "Monthly Bills"},
            format="json",
        )

        assert response.status_code == http_client.OK
        category.refresh_from_db()
        assert category.name == "Monthly Bills"
        assert category.updated_by_id == user.id

    def test_top_level_category_can_change_transaction_type(self, client):
        user = self._auth(client, username="category_change_type")
        expense_type = self._txn_type(TxnType.EXPENSES)
        income_type = self._txn_type(TxnType.INCOME)
        category = Category.objects.create(
            name="Flexible",
            transaction_type=expense_type,
            created_by=user,
        )

        response = client.patch(
            reverse("ledger:category-detail", args=[category.id]),
            {"transaction_type_id": income_type.id},
            format="json",
        )

        assert response.status_code == http_client.OK
        category.refresh_from_db()
        assert category.transaction_type_id == income_type.id

    def test_child_category_cannot_change_transaction_type_independently(self, client):
        user = self._auth(client, username="category_child_type")
        expense_type = self._txn_type(TxnType.EXPENSES)
        income_type = self._txn_type(TxnType.INCOME)
        parent = Category.objects.create(
            name="Parent",
            transaction_type=expense_type,
            created_by=user,
        )
        child = Category.objects.create(
            name="Child",
            transaction_type=expense_type,
            parent_category=parent,
            created_by=user,
        )

        response = client.patch(
            reverse("ledger:category-detail", args=[child.id]),
            {"transaction_type_id": income_type.id},
            format="json",
        )

        assert response.status_code == http_client.BAD_REQUEST
        assert response.data == {
            "transaction_type_id": [
                "Child categories must use the same transaction type as their parent category."
            ]
        }

        child.refresh_from_db()
        assert child.transaction_type_id == expense_type.id

    def test_delete_leaf_category_hard_deletes_it(self, client):
        user = self._auth(client, username="category_delete")
        expense_type = self._txn_type()
        category = Category.objects.create(
            name="Disposable",
            transaction_type=expense_type,
            created_by=user,
        )

        response = client.delete(reverse("ledger:category-detail", args=[category.id]))

        assert response.status_code == http_client.NO_CONTENT
        assert Category.objects.filter(pk=category.id).exists() is False

    def test_cannot_access_other_users_category(self, client):
        self._auth(client, username="category_owner")
        other = factories.User(username="category_other_owner", password="password123")
        expense_type = self._txn_type()
        other_category = Category.objects.create(
            name="Private Category",
            transaction_type=expense_type,
            created_by=other,
        )

        response = client.get(reverse("ledger:category-detail", args=[other_category.id]))

        assert response.status_code == http_client.NOT_FOUND
