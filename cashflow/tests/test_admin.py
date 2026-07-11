from datetime import date
from decimal import Decimal
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from cashflow.models import CashFlowEntry, Category, Status, Subcategory, TransactionType


class CashFlowAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="test-password",
        )
        cls.business = Status.objects.get(name="Бизнес")
        cls.personal = Status.objects.get(name="Личное")
        cls.tax = Status.objects.get(name="Налог")
        cls.expense_type = TransactionType.objects.get(name="Списание")
        cls.income_type = TransactionType.objects.get(name="Пополнение")
        cls.marketing = Category.objects.get(
            transaction_type=cls.expense_type,
            name="Маркетинг",
        )
        cls.infrastructure = Category.objects.get(
            transaction_type=cls.expense_type,
            name="Инфраструктура",
        )
        cls.avito = Subcategory.objects.get(category=cls.marketing, name="Avito")
        cls.vps = Subcategory.objects.get(category=cls.infrastructure, name="VPS")
        cls.sales = Category.objects.create(
            transaction_type=cls.income_type,
            name="Продажи",
        )
        cls.clients = Subcategory.objects.create(
            category=cls.sales,
            name="Клиенты",
        )
        cls.first = CashFlowEntry.objects.create(
            operation_date=date(2025, 1, 1),
            status=cls.business,
            subcategory=cls.avito,
            amount=Decimal("100.00"),
            comment="server advertising",
        )
        cls.second = CashFlowEntry.objects.create(
            operation_date=date(2025, 1, 10),
            status=cls.personal,
            subcategory=cls.vps,
            amount=Decimal("200.00"),
            comment="infrastructure",
        )
        cls.third = CashFlowEntry.objects.create(
            operation_date=date(2025, 2, 1),
            status=cls.tax,
            subcategory=cls.clients,
            amount=Decimal("300.00"),
            comment="income",
        )

    def setUp(self):
        self.client.force_login(self.user)
        self.changelist_url = reverse("admin:cashflow_cashflowentry_changelist")
        self.add_url = reverse("admin:cashflow_cashflowentry_add")

    @staticmethod
    def result_ids(response):
        return set(response.context["cl"].queryset.values_list("pk", flat=True))

    def test_root_and_login_redirects(self):
        response = self.client.get(reverse("root"))
        self.assertRedirects(
            response,
            self.changelist_url,
            fetch_redirect_response=False,
        )

        self.client.logout()
        response = self.client.get(self.changelist_url)
        expected = f"{reverse('admin:login')}?next={self.changelist_url}"
        self.assertRedirects(response, expected)

    def test_entry_form_required_fields_and_subcategory_labels(self):
        response = self.client.get(self.add_url)
        self.assertEqual(response.status_code, 200)
        form = response.context["adminform"].form
        for field_name in (
            "operation_date",
            "status",
            "transaction_type",
            "category",
            "subcategory",
            "amount",
        ):
            self.assertTrue(form.fields[field_name].required)
        self.assertFalse(form.fields["comment"].required)
        labels = [str(label) for _, label in form.fields["subcategory"].choices]
        self.assertIn("Списание -> Маркетинг -> Avito", labels)

    def test_cascade_helper_fields_prefilled_and_validated(self):
        change_url = reverse(
            "admin:cashflow_cashflowentry_change",
            args=(self.first.pk,),
        )
        response = self.client.get(change_url)
        self.assertEqual(response.status_code, 200)
        form = response.context["adminform"].form
        self.assertEqual(form.fields["category"].initial, self.marketing.pk)
        self.assertEqual(
            form.fields["transaction_type"].initial,
            self.expense_type.pk,
        )
        # data-атрибуты на пунктах селектов нужны js-каскаду
        self.assertContains(response, f'data-category="{self.marketing.pk}"')
        self.assertContains(response, f'data-type="{self.expense_type.pk}"')

        # тип не совпадает с категорией, а категория с подкатегорией
        response = self.client.post(
            self.add_url,
            {
                "operation_date": "2025-03-01",
                "status": self.business.pk,
                "transaction_type": self.income_type.pk,
                "category": self.marketing.pk,
                "subcategory": self.vps.pk,
                "amount": "10.00",
            },
        )
        self.assertEqual(response.status_code, 200)
        errors = response.context["adminform"].form.errors
        self.assertIn("category", errors)
        self.assertIn("subcategory", errors)

    def test_reference_filters(self):
        response = self.client.get(
            self.changelist_url,
            {"status__id__exact": self.business.pk},
        )
        self.assertSetEqual(self.result_ids(response), {self.first.pk})

        response = self.client.get(
            self.changelist_url,
            {"subcategory__category__id__exact": self.infrastructure.pk},
        )
        self.assertSetEqual(self.result_ids(response), {self.second.pk})

    def test_date_range_filter(self):
        response = self.client.get(
            self.changelist_url,
            {"operation_date__gte": "2025-01-01", "operation_date__lte": "2025-01-10"},
        )
        self.assertSetEqual(self.result_ids(response), {self.first.pk, self.second.pk})

        # битая дата не должна ронять страницу, фильтр просто игнорируется
        response = self.client.get(
            self.changelist_url,
            {"operation_date__gte": "not-a-date"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertSetEqual(
            self.result_ids(response),
            {self.first.pk, self.second.pk, self.third.pk},
        )

        # период работает вместе с остальными фильтрами
        response = self.client.get(
            self.changelist_url,
            {
                "operation_date__gte": "2025-01-01",
                "operation_date__lte": "2025-01-31",
                "status__id__exact": self.business.pk,
            },
        )
        self.assertSetEqual(self.result_ids(response), {self.first.pk})

    def test_date_filter_preserves_search_sorting_and_other_filters(self):
        parameters = {
            "operation_date__gte": "2025-01-01",
            "operation_date__lte": "2025-01-31",
            "status__id__exact": str(self.business.pk),
            "q": "server",
            "o": "1",
        }
        response = self.client.get(self.changelist_url, parameters)
        self.assertEqual(response.status_code, 200)
        date_filter = response.context["cl"].filter_specs[0]
        choice = next(date_filter.choices(response.context["cl"]))
        hidden = dict(choice["hidden_parameters"])
        self.assertEqual(hidden["q"], "server")
        self.assertEqual(hidden["o"], "1")
        self.assertEqual(hidden["status__id__exact"], str(self.business.pk))
        self.assertNotIn("operation_date__gte", hidden)
        self.assertNotIn("operation_date__lte", hidden)

        reset_params = parse_qs(urlsplit(choice["reset_query"]).query)
        self.assertEqual(reset_params["q"], ["server"])
        self.assertEqual(reset_params["o"], ["1"])
        self.assertEqual(reset_params["status__id__exact"], [str(self.business.pk)])
        self.assertNotIn("operation_date__gte", reset_params)
        self.assertNotIn("operation_date__lte", reset_params)

    def test_invalid_amount_is_rejected_by_admin(self):
        response = self.client.post(
            self.add_url,
            {
                "operation_date": "2025-03-01",
                "status": self.business.pk,
                "transaction_type": self.expense_type.pk,
                "category": self.marketing.pk,
                "subcategory": self.avito.pk,
                "amount": "0",
                "comment": "invalid",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("amount", response.context["adminform"].form.errors)

    def test_entry_admin_crud_flow(self):
        response = self.client.post(
            self.add_url,
            {
                "operation_date": "2025-03-01",
                "status": self.business.pk,
                "transaction_type": self.expense_type.pk,
                "category": self.marketing.pk,
                "subcategory": self.avito.pk,
                "amount": "450.00",
                "comment": "crud-entry",
                "_save": "Сохранить",
            },
        )
        self.assertEqual(response.status_code, 302)
        entry = CashFlowEntry.objects.get(comment="crud-entry")

        change_url = reverse("admin:cashflow_cashflowentry_change", args=(entry.pk,))
        response = self.client.post(
            change_url,
            {
                "operation_date": "2025-03-02",
                "status": self.personal.pk,
                "transaction_type": self.expense_type.pk,
                "category": self.infrastructure.pk,
                "subcategory": self.vps.pk,
                "amount": "500.00",
                "comment": "crud-entry-updated",
                "_save": "Сохранить",
            },
        )
        self.assertEqual(response.status_code, 302)
        entry.refresh_from_db()
        self.assertEqual(entry.comment, "crud-entry-updated")
        self.assertEqual(entry.amount, Decimal("500.00"))

        delete_url = reverse("admin:cashflow_cashflowentry_delete", args=(entry.pk,))
        response = self.client.post(delete_url, {"post": "yes"})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(CashFlowEntry.objects.filter(pk=entry.pk).exists())

    def test_dictionary_admin_crud_flow(self):
        response = self.client.post(
            reverse("admin:cashflow_transactiontype_add"),
            {"name": "Перевод", "_save": "Сохранить"},
        )
        self.assertEqual(response.status_code, 302)
        transaction_type = TransactionType.objects.get(name="Перевод")

        response = self.client.post(
            reverse("admin:cashflow_category_add"),
            {
                "name": "Между счетами",
                "transaction_type": transaction_type.pk,
                "_save": "Сохранить",
            },
        )
        self.assertEqual(response.status_code, 302)
        category = Category.objects.get(name="Между счетами")

        response = self.client.post(
            reverse("admin:cashflow_subcategory_add"),
            {
                "name": "Основной счет",
                "category": category.pk,
                "_save": "Сохранить",
            },
        )
        self.assertEqual(response.status_code, 302)
        subcategory = Subcategory.objects.get(name="Основной счет")

        response = self.client.post(
            reverse("admin:cashflow_subcategory_change", args=(subcategory.pk,)),
            {
                "name": "Резервный счет",
                "category": category.pk,
                "_save": "Сохранить",
            },
        )
        self.assertEqual(response.status_code, 302)
        subcategory.refresh_from_db()
        self.assertEqual(subcategory.name, "Резервный счет")

        for model_name, instance in (
            ("subcategory", subcategory),
            ("category", category),
            ("transactiontype", transaction_type),
        ):
            delete_url = reverse(
                f"admin:cashflow_{model_name}_delete",
                args=(instance.pk,),
            )
            response = self.client.post(delete_url, {"post": "yes"})
            self.assertEqual(response.status_code, 302)

        self.assertFalse(TransactionType.objects.filter(pk=transaction_type.pk).exists())
