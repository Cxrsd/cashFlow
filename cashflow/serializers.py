from rest_framework import serializers

from .models import CashFlowEntry


class CashFlowEntrySerializer(serializers.ModelSerializer):
    # категория и тип вычисляются по подкатегории, поэтому только чтение
    category = serializers.CharField(
        source="subcategory.category.name",
        read_only=True,
    )
    transaction_type = serializers.CharField(
        source="subcategory.category.transaction_type.name",
        read_only=True,
    )
    status_name = serializers.CharField(source="status.name", read_only=True)
    subcategory_name = serializers.CharField(
        source="subcategory.name",
        read_only=True,
    )

    class Meta:
        model = CashFlowEntry
        fields = (
            "id",
            "operation_date",
            "status",
            "status_name",
            "transaction_type",
            "category",
            "subcategory",
            "subcategory_name",
            "amount",
            "comment",
        )
