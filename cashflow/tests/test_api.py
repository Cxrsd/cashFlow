from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from cashflow.models import CashFlowEntry, Category, Status, Subcategory, TransactionType


class CashFlowApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="employee",
            password="test-password",
            is_staff=True,
        )
        cls.regular_user = get_user_model().objects.create_user(
            username="regular",
            password="test-password",
        )
        cls.business = Status.objects.get(name="Бизнес")
        cls.personal = Status.objects.get(name="Личное")
        cls.expense_type = TransactionType.objects.get(name="Списание")
        cls.marketing = Category.objects.get(
            transaction_type=cls.expense_type,
            name="Маркетинг",
        )
        cls.avito = Subcategory.objects.get(category=cls.marketing, name="Avito")
        cls.vps = Subcategory.objects.get(name="VPS")
        cls.first = CashFlowEntry.objects.create(
            operation_date=date(2025, 1, 1),
            status=cls.business,
            subcategory=cls.avito,
            amount=Decimal("100.00"),
        )
        cls.second = CashFlowEntry.objects.create(
            operation_date=date(2025, 2, 1),
            status=cls.personal,
            subcategory=cls.vps,
            amount=Decimal("200.00"),
        )
        cls.list_url = reverse("entry-list")

    def setUp(self):
        self.client.force_login(self.user)

    def result_ids(self, **params):
        response = self.client.get(self.list_url, params)
        self.assertEqual(response.status_code, 200)
        return {row["id"] for row in response.json()["results"]}

    def test_api_is_staff_only(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.list_url).status_code, 403)

        self.client.force_login(self.regular_user)
        self.assertEqual(self.client.get(self.list_url).status_code, 403)

    def test_list_returns_derived_classification(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        row = next(
            row for row in response.json()["results"] if row["id"] == self.first.pk
        )
        self.assertEqual(row["transaction_type"], "Списание")
        self.assertEqual(row["category"], "Маркетинг")
        self.assertEqual(row["subcategory_name"], "Avito")
        self.assertEqual(row["status_name"], "Бизнес")
        self.assertEqual(row["amount"], "100.00")

    def test_filters(self):
        self.assertEqual(
            self.result_ids(date_from="2025-01-01", date_to="2025-01-31"),
            {self.first.pk},
        )
        self.assertEqual(
            self.result_ids(category=self.marketing.pk),
            {self.first.pk},
        )

    def test_invalid_filter_values_are_ignored(self):
        self.assertEqual(
            self.result_ids(date_from="not-a-date", status="abc"),
            {self.first.pk, self.second.pk},
        )

    def test_create_and_delete_entry(self):
        response = self.client.post(
            self.list_url,
            {
                "operation_date": "2025-03-01",
                "status": self.business.pk,
                "subcategory": self.avito.pk,
                "amount": "450.00",
                "comment": "api-entry",
            },
        )
        self.assertEqual(response.status_code, 201)
        entry_id = response.json()["id"]

        detail_url = reverse("entry-detail", args=(entry_id,))
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(CashFlowEntry.objects.filter(pk=entry_id).exists())

    def test_create_rejects_invalid_amount(self):
        response = self.client.post(
            self.list_url,
            {
                "operation_date": "2025-03-01",
                "status": self.business.pk,
                "subcategory": self.avito.pk,
                "amount": "0",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("amount", response.json())
