from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("ledger", "0010_rename_ledger_acco_account_8dcb52_idx_ledger_acco_account_30b40d_idx_and_more"),
        ("users", "0005_account_is_savings"),
    ]

    operations = [
        migrations.CreateModel(
            name="Budget",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("year", models.PositiveIntegerField()),
                ("month", models.PositiveSmallIntegerField()),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("spent_amount", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("account", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="budgets", to="users.account")),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="budgets", to="ledger.category")),
                ("created_by", models.ForeignKey(blank=True, help_text="User who created this object", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="budget_created", to="users.user")),
                ("deleted_by", models.ForeignKey(blank=True, help_text="User who deleted this object", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="budget_deleted", to="users.user")),
                ("updated_by", models.ForeignKey(blank=True, help_text="User who last updated this object", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="budget_updated", to="users.user")),
            ],
            options={
                "ordering": ["-year", "-month", "-id"],
                "unique_together": {("account", "category", "year", "month")},
            },
        ),
    ]
