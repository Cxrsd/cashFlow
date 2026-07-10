from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Status(models.Model):
    name = models.CharField("Название", max_length=100, unique=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "Статус"
        verbose_name_plural = "Статусы"

    def __str__(self):
        return self.name


class TransactionType(models.Model):
    name = models.CharField("Название", max_length=100, unique=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "Тип операции"
        verbose_name_plural = "Типы операций"

    def __str__(self):
        return self.name


class Category(models.Model):
    # расходы/доходы, привязаны к типу операции
    name = models.CharField("Название", max_length=100)
    transaction_type = models.ForeignKey(
        TransactionType,
        on_delete=models.PROTECT,
        related_name="categories",
        verbose_name="Тип операции",
    )

    class Meta:
        ordering = ("transaction_type__name", "name")
        constraints = (
            models.UniqueConstraint(
                fields=("transaction_type", "name"),
                name="cashflow_category_type_name_unique",
            ),
        )
        verbose_name = "Категория"
        verbose_name_plural = "Категории"

    def __str__(self):
        return f"{self.transaction_type} -> {self.name}"


class Subcategory(models.Model):
    name = models.CharField("Название", max_length=100)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="subcategories",
        verbose_name="Категория",
    )

    class Meta:
        ordering = (
            "category__transaction_type__name",
            "category__name",
            "name",
        )
        constraints = (
            models.UniqueConstraint(
                fields=("category", "name"),
                name="cashflow_subcategory_category_name_unique",
            ),
        )
        verbose_name = "Подкатегория"
        verbose_name_plural = "Подкатегории"

    def __str__(self):
        return f"{self.category} -> {self.name}"


class CashFlowEntry(models.Model):
    """Операция ДДС. Категория и тип не хранятся, вычисляются через подкатегорию"""

    operation_date = models.DateField(
        "Дата операции",
        default=timezone.localdate,
        db_index=True,
    )
    status = models.ForeignKey(
        Status,
        on_delete=models.PROTECT,
        related_name="entries",
        verbose_name="Статус",
    )
    subcategory = models.ForeignKey(
        Subcategory,
        on_delete=models.PROTECT,
        related_name="entries",
        verbose_name="Подкатегория",
        help_text="Тип и категория определяются выбранным полным путем.",
    )
    amount = models.DecimalField(
        "Сумма, ₽",
        max_digits=14,
        decimal_places=2,
        validators=(MinValueValidator(Decimal("0.01")),),
    )
    comment = models.TextField("Комментарий", blank=True)

    class Meta:
        ordering = ("-operation_date", "-pk")
        constraints = (
            models.CheckConstraint(
                condition=models.Q(amount__gte=Decimal("0.01")),
                name="cashflow_entry_amount_gte_001",
            ),
        )
        verbose_name = "Операция ДДС"
        verbose_name_plural = "Операции ДДС"

    @property
    def category(self):
        return self.subcategory.category

    @property
    def transaction_type(self):
        return self.category.transaction_type

    def __str__(self):
        return f"{self.operation_date.isoformat()}: {self.amount:.2f} ₽"
