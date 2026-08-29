from django.urls import path

from . import api, views

app_name = "catalog"

urlpatterns = [
    path("", views.EntryListView.as_view(), name="entry-list"),
    path("entries/<slug:slug>/", views.EntryDetailView.as_view(), name="entry-detail"),
    path("entries/<slug:slug>/reviews/new/", views.ReviewCreateView.as_view(), name="review-create"),
    path(
        "entries/<slug:slug>/reviews/<int:review_pk>/edit/",
        views.ReviewUpdateView.as_view(),
        name="review-update",
    ),
    path(
        "entries/<slug:slug>/reviews/<int:review_pk>/delete/",
        views.ReviewDeleteView.as_view(),
        name="review-delete",
    ),
    path("submissions/new/", views.SubmissionCreateView.as_view(), name="submission-create"),
    path("submissions/mine/", views.SubmissionListView.as_view(), name="submission-list"),
    path("api/entries/", api.entry_list_api, name="api-entry-list"),
    path("api/entries/<slug:slug>/", api.entry_detail_api, name="api-entry-detail"),
]
