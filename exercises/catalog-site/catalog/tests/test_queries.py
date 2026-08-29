from django.test import TestCase

from catalog.models import Entry
from catalog.queries import filter_published_entries

from .base import CatalogTestDataMixin


class PublishedEntryQueryTests(CatalogTestDataMixin, TestCase):
    def test_public_query_never_returns_draft(self):
        self.assertEqual(list(filter_published_entries({})), [self.published])

    def test_search_matches_summary(self):
        queryset = filter_published_entries({"q": "used by tests"})
        self.assertEqual(list(queryset), [self.published])

    def test_category_and_tag_filters_can_be_combined(self):
        queryset = filter_published_entries(
            {"category": self.category.slug, "tag": self.tag.slug}
        )
        self.assertEqual(list(queryset), [self.published])

    def test_unknown_filter_key_is_ignored(self):
        queryset = filter_published_entries({"status": Entry.Status.DRAFT})
        self.assertEqual(list(queryset), [self.published])

    def test_category_and_tags_are_preloaded(self):
        with self.assertNumQueries(2):
            entries = list(filter_published_entries({}))
            self.assertEqual(entries[0].category.name, "Games")
            self.assertEqual([tag.slug for tag in entries[0].tags.all()], ["reference"])
