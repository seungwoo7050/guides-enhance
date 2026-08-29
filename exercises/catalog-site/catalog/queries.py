"""Reusable queries for public catalog pages and API responses."""

from __future__ import annotations

from collections.abc import Mapping

from django.db.models import Prefetch, Q, QuerySet

from .models import Entry, Review


def published_entries() -> QuerySet[Entry]:
    return (
        Entry.objects.published()
        .select_related("category", "created_by")
        .prefetch_related("tags")
    )


# [Implementation 7]
# Only named filters are accepted; request parameters are never expanded directly into ORM lookups.
def filter_published_entries(parameters: Mapping[str, str]) -> QuerySet[Entry]:
    queryset = published_entries()

    term = parameters.get("q", "").strip()
    if term:
        queryset = queryset.filter(
            Q(title__icontains=term)
            | Q(summary__icontains=term)
            | Q(description__icontains=term)
        )

    category = parameters.get("category", "").strip()
    if category:
        queryset = queryset.filter(category__slug=category)

    tag = parameters.get("tag", "").strip()
    if tag:
        queryset = queryset.filter(tags__slug=tag)

    return queryset.distinct()


def published_entry_detail() -> QuerySet[Entry]:
    visible_reviews = Review.objects.filter(is_visible=True).select_related("author")
    return published_entries().prefetch_related(
        Prefetch("reviews", queryset=visible_reviews, to_attr="visible_reviews")
    )
