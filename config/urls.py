from django.contrib import admin
from django.urls import path
from django.views.generic import RedirectView


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
]
