from django.contrib import admin
from ledger.models import Place, TransactionType, RecurringTransaction, Category, \
Transaction, Receipt, Store, Tag


class CategoryAdmin(admin.ModelAdmin):
    search_fields = ["id", "category__name"]
    list_display = ["id", "name", "color", "icon", "created_by"]

class StoreAdmin(admin.ModelAdmin):
    search_fields = ["id", "name"]
    list_display = ["id", "name", "created_by","deleted_at"]
    list_filter = ["deleted_at"]

class PlaceAdmin(admin.ModelAdmin):
    search_fields = ["id", "name"]
    list_display = ["id", "name", "created_by", "deleted_at"]
    list_filter = ["deleted_at"]

class ReceiptAdmin(admin.ModelAdmin):
    search_fields = ["id", "transaction"]
    list_display = ["id", "transaction", "created_by", "deleted_at"]
    list_filter = ["deleted_at"]

class RecurringTransactionAdmin(admin.ModelAdmin):
    search_fields = ["id", "name"]
    list_display = ["id", "name",  "created_by", "deleted_at"]
    list_filter = ["deleted_at"]

class TagAdmin(admin.ModelAdmin):
    search_fields = ["id", "name"]
    list_display = ["id", "name", "color", "created_by__id"]
    list_filter = ["deleted_at"]


class TransactionTypeAdmin(admin.ModelAdmin):
    search_fields = ["id", "name"]
    list_display = ["id", "name", "color", "icon",  "created_by", "deleted_at"]
    list_filter = ["deleted_at"]


class TransactionAdmin(admin.ModelAdmin):
    search_fields = ["id", "transaction__name"]
    list_display = ["id", "name", "user_id", "deleted_at"]
    list_filter = ["deleted_at"]

class TransactionTagAdmin(admin.ModelAdmin):
    search_fields = ["id", "transaction", "tag"]
    list_display = ["id", "transaction", "tag","deleted_at"]
    list_filter = ["deleted_at"]

admin.site.register(Category, CategoryAdmin)
admin.site.register(Store, StoreAdmin)
admin.site.register(Place, PlaceAdmin)
admin.site.register(Receipt, ReceiptAdmin)
admin.site.register(RecurringTransaction, RecurringTransactionAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(Transaction, TransactionAdmin)
admin.site.register(TransactionType, TransactionTypeAdmin)
