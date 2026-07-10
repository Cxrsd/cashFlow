from datetime import date

from django import forms
from django.contrib import admin
from django.db import models

from .forms import CashFlowEntryForm
from .models import CashFlowEntry, Category, Status, Subcategory, TransactionType


class DateRangeFieldListFilter(admin.FieldListFilter):
    """Фильтр по произвольному периоду дат, штатного такого нет"""

    template = "admin/cashflow/date_range_filter.html"

    def __init__(self, field, request, params, model, model_admin, field_path):
        self.lookup_kwarg_from = f"{field_path}__gte"
        self.lookup_kwarg_to = f"{field_path}__lte"
        super().__init__(field, request, params, model, model_admin, field_path)

    def expected_parameters(self):
        return (self.lookup_kwarg_from, self.lookup_kwarg_to)

    def choices(self, changelist):
        # остальные GET-параметры прокидываем скрытыми полями, чтобы форма их не сбрасывала
        excluded = {*self.expected_parameters(), "p", "e"}
        hidden_parameters = [
            (key, value)
            for key, values in self.request.GET.lists()
            if key not in excluded
            for value in values
        ]
        yield {
            "from_value": self.request.GET.get(self.lookup_kwarg_from, ""),
            "to_value": self.request.GET.get(self.lookup_kwarg_to, ""),
            "hidden_parameters": hidden_parameters,
            "reset_query": changelist.get_query_string(
                remove=[*self.expected_parameters(), "p", "e"]
            ),
        }

    def queryset(self, request, queryset):
        for lookup in self.expected_parameters():
            raw_value = request.GET.get(lookup)
            if not raw_value:
                continue
            try:
                value = date.fromisoformat(raw_value)
            except ValueError:
                continue  # невалидную дату пропускаем
            queryset = queryset.filter(**{lookup: value})
        return queryset


@admin.register(Status)
class StatusAdmin(admin.ModelAdmin):
    list_display = ("name",)
    ordering = ("name",)
    search_fields = ("name",)


@admin.register(TransactionType)
class TransactionTypeAdmin(admin.ModelAdmin):
    list_display = ("name",)
    ordering = ("name",)
    search_fields = ("name",)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "transaction_type")
    list_filter = ("transaction_type",)
    list_select_related = ("transaction_type",)
    search_fields = ("name", "transaction_type__name")


@admin.register(Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "category_name", "transaction_type_name")
    list_filter = ("category__transaction_type", "category")
    list_select_related = ("category__transaction_type",)
    search_fields = (
        "name",
        "category__name",
        "category__transaction_type__name",
    )

    @admin.display(ordering="category__name", description="Категория")
    def category_name(self, obj):
        return obj.category.name

    @admin.display(
        ordering="category__transaction_type__name",
        description="Тип операции",
    )
    def transaction_type_name(self, obj):
        return obj.category.transaction_type.name


@admin.register(CashFlowEntry)
class CashFlowEntryAdmin(admin.ModelAdmin):
    form = CashFlowEntryForm
    fields = (
        "operation_date",
        "status",
        "transaction_type",
        "category",
        "subcategory",
        "amount",
        "comment",
    )
    list_display = (
        "operation_date",
        "status",
        "transaction_type_name",
        "category_name",
        "subcategory_name",
        "amount",
        "comment",
    )
    list_display_links = ("operation_date",)
    list_filter = (
        ("operation_date", DateRangeFieldListFilter),
        "status",
        "subcategory__category__transaction_type",
        "subcategory__category",
        "subcategory",
    )
    list_per_page = 50
    list_select_related = ("status", "subcategory__category__transaction_type")
    search_fields = (
        "comment",
        "status__name",
        "subcategory__name",
        "subcategory__category__name",
        "subcategory__category__transaction_type__name",
    )
    show_facets = admin.ShowFacets.NEVER
    formfield_overrides = {
        models.DecimalField: {
            "widget": forms.NumberInput(attrs={"min": "0.01", "step": "0.01"})
        }
    }

    @admin.display(
        ordering="subcategory__category__transaction_type__name",
        description="Тип",
    )
    def transaction_type_name(self, obj):
        return obj.transaction_type.name

    @admin.display(ordering="subcategory__category__name", description="Категория")
    def category_name(self, obj):
        return obj.category.name

    @admin.display(ordering="subcategory__name", description="Подкатегория")
    def subcategory_name(self, obj):
        return obj.subcategory.name


admin.site.site_header = "Учет движения денежных средств"
admin.site.site_title = "ДДС"
admin.site.index_title = "Управление данными"
