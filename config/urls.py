from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from rest_framework.routers import DefaultRouter

from cashflow.views import CashFlowEntryViewSet

router = DefaultRouter()
router.register("entries", CashFlowEntryViewSet, basename="entry")

urlpatterns = [
    path(
        "",
        RedirectView.as_view(
            pattern_name="admin:cashflow_cashflowentry_changelist",
            permanent=False,
        ),
        name="root",
    ),
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
]
