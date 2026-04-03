from __future__ import annotations

from django.conf import settings
from django.db import models

from core.models import CommonInfo
from ledger.constants import ACTION_CHOICES
from ledger.querysets.transactions import TransactionQuerySet

class Tag(CommonInfo):
    name = models.CharField(max_length=150)
    color = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        unique_together = ('created_by', 'name')
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
    
class Place(CommonInfo):
    name = models.CharField(max_length=255, help_text='Woerden, Utrecht, Online')

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class TransactionType(CommonInfo):
    name = models.CharField(max_length=50, help_text='Debit, Credit, Transfer (for accounts)')
    color = models.CharField(max_length=20)
    icon = models.CharField(max_length=100)
    notes = models.CharField(max_length=300, blank=True, null=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Category(CommonInfo):
    name = models.CharField(max_length=100, help_text='Salary, Food, Insurance, Housing')
    transaction_type = models.ForeignKey(TransactionType, related_name='categories', on_delete=models.CASCADE)
    parent_category = models.ForeignKey('Category', on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.CharField(max_length=100, blank=True, null=True)
    color = models.CharField(max_length=20, blank=True, null=True)
    icon = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
    

class Store(CommonInfo):
    name = models.CharField(max_length=255, help_text='Woerden, Utrecht, Online')

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

class RecurringTransaction(CommonInfo):
    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='recurring_transactions', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES)
    interval = models.PositiveIntegerField(default=1, help_text='every 1 month, every 2 weeks')
    notes = models.CharField(max_length=500, blank=True, null=True)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.user})"


class Transaction(CommonInfo):
    account = models.ForeignKey('users.Account', related_name='transactions', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='transactions', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=50, decimal_places=2, blank=True, null=True, help_text='Amount of the transaction')
    name = models.CharField(max_length=500)
    notes = models.CharField(max_length=500, blank=True, null=True)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, help_text='when category type is debit, salary net')
    gross_amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, help_text='when category type is debit, salary gross')
    debit_month_year = models.DateField(blank=True, null=True, help_text='when category type is debit, salary month and year')

    transaction_type = models.ForeignKey(TransactionType, related_name='transactions', on_delete=models.SET_NULL, null=True, blank=True)
    category = models.ForeignKey(Category, related_name='transactions', on_delete=models.SET_NULL, null=True, blank=True)
    store = models.ForeignKey(Store, related_name='transactions', on_delete=models.SET_NULL, null=True, blank=True)
    place = models.ForeignKey(Place, related_name='transactions', on_delete=models.SET_NULL, null=True, blank=True)

    external_transaction_id = models.PositiveIntegerField(unique=True, null=True, blank=True)
    pair_transaction = models.ForeignKey('users.Account', related_name='pair_transaction', on_delete=models.SET_NULL, null=True, blank=True)
    is_recurring = models.BooleanField(default=False, help_text='only for recurring transactions')
    recurring = models.ForeignKey(RecurringTransaction, related_name='recurring_transactions', on_delete=models.SET_NULL, null=True, blank=True)
    is_refunded = models.BooleanField(default=False, help_text='only for credits')
    refunded_at = models.DateTimeField(blank=True, null=True, help_text='only for credits')
    transaction_at = models.DateTimeField(null=True, blank=True, help_text='Datetime when the transaction happened')
    previous_balance = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    pair_previous_balance = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    tags = models.ManyToManyField(Tag, related_name="transactions", blank=True)

    objects = TransactionQuerySet.as_manager()
    
    def __str__(self) -> str:
        return f"{self.name} ({self.amount})"
    
    class Meta:
        ordering = ["-id"] 
        

class Receipt(CommonInfo):
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='receipts')
    data = models.JSONField()

    def __str__(self) -> str:
        return f'Receipt for Transaction {self.transaction.id}'


class TransactionLog(models.Model):

    transaction = models.ForeignKey(
        "Transaction",
        related_name="logs",
        on_delete=models.SET_NULL,
        null=True, 
        blank=True
    )

    action = models.CharField(max_length=20, choices=ACTION_CHOICES)

    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="transaction_logs",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    old_data = models.JSONField(null=True, blank=True)
    new_data = models.JSONField(null=True, blank=True)
    note = models.CharField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=["transaction", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"TransactionLog #{self.id} - {self.action}"
