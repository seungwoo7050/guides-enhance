"""Server-rendered catalog views."""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import ReviewForm, SubmissionForm
from .models import Category, Entry, Review, Submission, Tag
from .queries import filter_published_entries, published_entry_detail


# [Implementation 6]
# The first public route returns only published entries and keeps pagination stable.
class EntryListView(ListView):
    template_name = "catalog/entry_list.html"
    context_object_name = "entries"
    paginate_by = 12

    def get_queryset(self):
        return filter_published_entries(self.request.GET)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "categories": Category.objects.all(),
                "tags": Tag.objects.all(),
                "current_q": self.request.GET.get("q", ""),
                "current_category": self.request.GET.get("category", ""),
                "current_tag": self.request.GET.get("tag", ""),
            }
        )
        return context


# [Implementation 10]
# Detail loading reuses the public filter and preloads only visible reviews with their authors.
class EntryDetailView(DetailView):
    template_name = "catalog/entry_detail.html"
    context_object_name = "entry"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return published_entry_detail()


class ReviewCreateView(LoginRequiredMixin, CreateView):
    form_class = ReviewForm
    template_name = "catalog/review_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.entry = get_object_or_404(Entry.objects.published(), slug=kwargs["slug"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["entry"] = self.entry
        return context

    def form_valid(self, form):
        if Review.objects.filter(entry=self.entry, author=self.request.user).exists():
            form.add_error(None, "이 항목에는 이미 후기를 작성했습니다.")
            return self.form_invalid(form)

        form.instance.entry = self.entry
        form.instance.author = self.request.user
        try:
            with transaction.atomic():
                response = super().form_valid(form)
        except IntegrityError:
            form.add_error(None, "이 항목에는 이미 후기를 작성했습니다.")
            return self.form_invalid(form)

        messages.success(self.request, "후기를 저장했습니다.")
        return response

    def get_success_url(self):
        return self.entry.get_absolute_url()


# [Implementation 11]
# Ownership is checked on the server; hiding edit links in templates is not an authorization check.
class ReviewAuthorRequiredMixin(UserPassesTestMixin):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("entry", "author")
            .filter(entry__slug=self.kwargs["slug"])
        )

    def test_func(self):
        return self.get_object().author_id == self.request.user.id


class ReviewUpdateView(
    LoginRequiredMixin,
    ReviewAuthorRequiredMixin,
    UpdateView,
):
    model = Review
    form_class = ReviewForm
    template_name = "catalog/review_form.html"
    pk_url_kwarg = "review_pk"

    def get_success_url(self):
        messages.success(self.request, "후기를 수정했습니다.")
        return self.object.entry.get_absolute_url()


class ReviewDeleteView(
    LoginRequiredMixin,
    ReviewAuthorRequiredMixin,
    DeleteView,
):
    model = Review
    template_name = "catalog/review_confirm_delete.html"
    pk_url_kwarg = "review_pk"

    def get_success_url(self):
        messages.success(self.request, "후기를 삭제했습니다.")
        return self.object.entry.get_absolute_url()


class SubmissionCreateView(LoginRequiredMixin, CreateView):
    form_class = SubmissionForm
    template_name = "catalog/submission_form.html"

    def form_valid(self, form):
        form.instance.submitted_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, "제보를 접수했습니다.")
        return response

    def get_success_url(self):
        return reverse("catalog:submission-list")


class SubmissionListView(LoginRequiredMixin, ListView):
    template_name = "catalog/submission_list.html"
    context_object_name = "submissions"
    paginate_by = 20

    def get_queryset(self):
        return Submission.objects.filter(submitted_by=self.request.user).select_related(
            "reviewed_by",
            "created_entry",
        )
