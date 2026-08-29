"""Read-only JSON endpoints for optional frontend integration."""

from __future__ import annotations

from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from .models import Entry
from .queries import filter_published_entries, published_entry_detail


def _entry_data(entry: Entry, request) -> dict[str, object]:
    return {
        "title": entry.title,
        "slug": entry.slug,
        "summary": entry.summary,
        "description": entry.description,
        "category": {
            "name": entry.category.name,
            "slug": entry.category.slug,
        },
        "tags": [{"name": tag.name, "slug": tag.slug} for tag in entry.tags.all()],
        "published_at": entry.published_at.isoformat() if entry.published_at else None,
        "url": request.build_absolute_uri(entry.get_absolute_url()),
    }


# [Implementation 14]
# The API serializes an explicit public field set instead of exposing model attributes wholesale.
@require_GET
def entry_list_api(request):
    queryset = filter_published_entries(request.GET)
    paginator = Paginator(queryset, 20)
    page = paginator.get_page(request.GET.get("page", "1"))
    return JsonResponse(
        {
            "count": paginator.count,
            "page": page.number,
            "pages": paginator.num_pages,
            "results": [_entry_data(entry, request) for entry in page.object_list],
        }
    )


@require_GET
def entry_detail_api(request, slug: str):
    entry = get_object_or_404(published_entry_detail(), slug=slug)
    data = _entry_data(entry, request)
    data["reviews"] = [
        {
            "author": str(review.author),
            "rating": review.rating,
            "body": review.body,
            "created_at": review.created_at.isoformat(),
        }
        for review in entry.visible_reviews
    ]
    return JsonResponse(data)
