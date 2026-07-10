from django import forms

from .models import CashFlowEntry, Category, Subcategory, TransactionType


class CategorySelect(forms.Select):
    # data-type на пунктах для cascade.js
    def create_option(self, name, value, *args, **kwargs):
        option = super().create_option(name, value, *args, **kwargs)
        if value:
            option["attrs"]["data-type"] = str(value.instance.transaction_type_id)
        return option


class SubcategorySelect(forms.Select):
    # data-category, аналогично
    def create_option(self, name, value, *args, **kwargs):
        option = super().create_option(name, value, *args, **kwargs)
        if value:
            option["attrs"]["data-category"] = str(value.instance.category_id)
        return option


class CashFlowEntryForm(forms.ModelForm):
    """Форма операции. Тип и категория чисто интерфейсные (каскад в cascade.js),
    в базу уходит только подкатегория"""

    transaction_type = forms.ModelChoiceField(
        queryset=TransactionType.objects.all(),
        required=True,
        label="Тип",
        help_text="Сужает список категорий",
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.select_related("transaction_type"),
        required=True,
        label="Категория",
        widget=CategorySelect,
        help_text="Сужает список подкатегорий",
    )

    class Meta:
        model = CashFlowEntry
        fields = ("operation_date", "status", "subcategory", "amount", "comment")
        widgets = {"subcategory": SubcategorySelect}

    class Media:
        js = ("cashflow/cascade.js",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # иначе N+1 на подписях пунктов
        self.fields["subcategory"].queryset = Subcategory.objects.select_related(
            "category__transaction_type"
        )
        if self.instance.pk:
            category = self.instance.subcategory.category
            self.fields["category"].initial = category.pk
            self.fields["transaction_type"].initial = category.transaction_type_id

    def clean(self):
        # подстраховка на случай выключенного js
        cleaned = super().clean()
        transaction_type = cleaned.get("transaction_type")
        category = cleaned.get("category")
        subcategory = cleaned.get("subcategory")
        if category and transaction_type and category.transaction_type_id != transaction_type.pk:
            self.add_error("category", "Категория не относится к выбранному типу")
        if subcategory and category and subcategory.category_id != category.pk:
            self.add_error("subcategory", "Подкатегория не относится к выбранной категории")
        return cleaned
