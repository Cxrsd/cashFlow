from django.core.exceptions import ValidationError
from rest_framework import viewsets

from .models import CashFlowEntry
from .serializers import CashFlowEntrySerializer


class CashFlowEntryViewSet(viewsets.ModelViewSet):
    """CRUD API операций, фильтры те же, что в changelist админки"""

    serializer_class = CashFlowEntrySerializer
    queryset = CashFlowEntry.objects.select_related(
        "status",
        "subcategory__category__transaction_type",
    )

    filter_lookups = {
        "date_from": "operation_date__gte",
        "date_to": "operation_date__lte",
        "status": "status_id",
        "type": "subcategory__category__transaction_type_id",
        "category": "subcategory__category_id",
        "subcategory": "subcategory_id",
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        for parameter, lookup in self.filter_lookups.items():
            value = self.request.query_params.get(parameter)
            if not value:
                continue
            try:
                queryset = queryset.filter(**{lookup: value})
            except (ValueError, ValidationError):
                continue  # битое значение игнорируем, как и админка
        return queryset
