from django.db import migrations


def add_initial_data(apps, schema_editor):
    Status = apps.get_model("cashflow", "Status")
    TransactionType = apps.get_model("cashflow", "TransactionType")
    Category = apps.get_model("cashflow", "Category")
    Subcategory = apps.get_model("cashflow", "Subcategory")

    for name in ("Бизнес", "Личное", "Налог"):
        Status.objects.get_or_create(name=name)

    TransactionType.objects.get_or_create(name="Пополнение")
    expense_type, _ = TransactionType.objects.get_or_create(name="Списание")

    hierarchy = {
        "Инфраструктура": ("VPS", "Proxy"),
        "Маркетинг": ("Farpost", "Avito"),
    }
    for category_name, subcategory_names in hierarchy.items():
        category, _ = Category.objects.get_or_create(
            transaction_type=expense_type,
            name=category_name,
        )
        for subcategory_name in subcategory_names:
            Subcategory.objects.get_or_create(
                category=category,
                name=subcategory_name,
            )


class Migration(migrations.Migration):
    dependencies = [("cashflow", "0001_initial")]

    operations = [
        migrations.RunPython(add_initial_data, migrations.RunPython.noop),
    ]

