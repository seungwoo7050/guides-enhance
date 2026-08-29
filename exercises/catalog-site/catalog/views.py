"""Server-rendered catalog views."""

from django.views.generic import ListView

from .models import Category, Tag
from .queries import filter_published_entries


# [Implementation 6]
class EntryListView(ListView):
    template_name = "catalog/entry_list.html"
    context_object_name = "entries"
    paginate_by = 12

    def get_queryset(self):
        return filter_published_entries(self.request.GET)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "categories": Category.objects.all(),
            "tags": Tag.objects.all(),
            "current_q": self.request.GET.get("q", ""),
            "current_category": self.request.GET.get("category", ""),
            "current_tag": self.request.GET.get("tag", ""),
        })
        return context
