from django.contrib import admin
from users.models import User

class UserAdmin(admin.ModelAdmin):
    search_fields = ["id", "first_name", "last_name", "email"]
    list_display = ["id", "first_name", "last_name"]

admin.site.register(User, UserAdmin)
