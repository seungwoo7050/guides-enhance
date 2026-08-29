from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.EntryListView.as_view(), name="entry-list"),
]
