from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.utils import timezone

from cashflow.models import CashFlowEntry, Category, Status, Subcategory, TransactionType


class SeedDataTests(TestCase):
    def test_initial_data_created(self):
        self.assertEqual(Status.objects.count(), 3)
        self.assertEqual(TransactionType.objects.count(), 2)
        self.assertTrue(
            Subcategory.objects.filter(
                name="Avito",
                category__name="Маркетинг",
                category__transaction_type__name="Списание",
            ).exists()
        )


class CashFlowModelTests(TestCase):
    def setUp(self):
        self.status = Status.objects.get(name="Бизнес")
        self.expense_type = TransactionType.objects.get(name="Списание")
        self.marketing = Category.objects.get(
            transaction_type=self.expense_type,
            name="Маркетинг",
        )
        self.avito = Subcategory.objects.get(category=self.marketing, name="Avito")

    def make_entry(self, **overrides):
        values = {
            "operation_date": date(2025, 1, 1),
            "status": self.status,
            "subcategory": self.avito,
            "amount": Decimal("1000.00"),
            "comment": "",
        }
        values.update(overrides)
        return CashFlowEntry(**values)

    def test_valid_entry_and_derived_classification(self):
        entry = self.make_entry()
        entry.full_clean()
        entry.save()

        self.assertEqual(entry.category, self.marketing)
        self.assertEqual(entry.transaction_type, self.expense_type)

    def test_default_date_is_today_and_editable(self):
        entry = CashFlowEntry.objects.create(
            status=self.status,
            subcategory=self.avito,
            amount=Decimal("10.00"),
        )
        self.assertEqual(entry.operation_date, timezone.localdate())

        entry.operation_date = date(2020, 2, 3)
        entry.save(update_fields=("operation_date",))
        entry.refresh_from_db()
        self.assertEqual(entry.operation_date, date(2020, 2, 3))

    def test_zero_and_negative_amounts_fail_validation(self):
        for amount in (Decimal("0.00"), Decimal("-1.00")):
            with self.assertRaises(ValidationError):
                self.make_entry(amount=amount).full_clean()

    def test_duplicates_within_parent_are_rejected(self):
        with self.assertRaises(ValidationError):
            Status(name="Бизнес").full_clean()
        with self.assertRaises(ValidationError):
            Category(
                transaction_type=self.expense_type,
                name="Маркетинг",
            ).full_clean()

    def test_same_name_is_allowed_under_different_parent(self):
        income_type = TransactionType.objects.get(name="Пополнение")
        category = Category(transaction_type=income_type, name="Маркетинг")
        category.full_clean()

    def test_reparenting_reclassifies_existing_entries(self):
        entry = self.make_entry()
        entry.save()
        income_type = TransactionType.objects.get(name="Пополнение")
        income_category = Category.objects.create(
            transaction_type=income_type,
            name="Продажи",
        )

        self.avito.category = income_category
        self.avito.save(update_fields=("category",))

        entry.refresh_from_db()
        self.assertEqual(entry.category, income_category)
        self.assertEqual(entry.transaction_type, income_type)

    def test_used_dictionary_values_are_protected_from_deletion(self):
        self.make_entry().save()

        with self.assertRaises(ProtectedError):
            self.avito.delete()
        with self.assertRaises(ProtectedError):
            self.status.delete()
