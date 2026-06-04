from django.contrib import admin
from users.models import User, Account


class UserAdmin(admin.ModelAdmin):
    search_fields = ["id", "first_name", "last_name", "email"]

    def get_list_display(self, request):
        return [field.name for field in self.model._meta.fields]


class AccountsAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "user",
        "name",
        "icon",
        "color",
        "balance",
        "count_in_assets",
        "is_default",
        "is_shared",
        "shared_user_list",
        "category_list",
        "notes",
        "created_by",
        "created_at",
        "updated_by",
        "updated_at",
        "deleted_by",
        "deleted_at",
    ]

    fieldsets = (
        ("Basic Info", {
            "fields": ("user", "name", "icon", "color"),
        }),
        ("Financial", {
            "fields": ("balance", "count_in_assets"),
        }),
        ("Sharing", {
            "fields": ("is_shared", "shared_users"),
        }),
        ("Settings", {
            "fields": ("is_default", "categories"),
        }),
        ("Notes", {
            "fields": ("notes",),
        }),
        ("Metadata", {
            "fields": (
                "created_by", "updated_by", "deleted_by",
                "created_at", "updated_at", "deleted_at"
            ),
        }),
    )

    readonly_fields = (
        "created_at", "updated_at", "deleted_at",
    )

    autocomplete_fields = ['shared_users', 'categories']

    @admin.display(description='Shared Users')
    def shared_user_list(self, obj):
        return ", ".join(obj.shared_users.values_list('username', flat=True))

    @admin.display(description='Categories')
    def category_list(self, obj):
        return ", ".join(obj.categories.values_list('name', flat=True))


admin.site.register(User, UserAdmin)
admin.site.register(Account, AccountsAdmin)