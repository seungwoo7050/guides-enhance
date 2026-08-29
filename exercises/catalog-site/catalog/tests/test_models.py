from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase

from catalog.models import Category, Entry, Review

from .base import CatalogTestDataMixin


# [Implementation 15]
# The suite locks down model constraints before testing HTTP behavior built on top of them.
class CatalogModelTests(CatalogTestDataMixin, TestCase):
    def test_published_manager_excludes_drafts(self):
        self.assertEqual(list(Entry.objects.published()), [self.published])

    def test_category_with_entries_is_protected(self):
        with self.assertRaises(ProtectedError):
            self.category.delete()

    def test_database_rejects_rating_outside_one_to_five(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Review.objects.create(
                    entry=self.published,
                    author=self.author,
                    rating=6,
                    body="This body is long enough for a valid review.",
                )

    def test_database_rejects_second_review_for_same_entry_and_author(self):
        Review.objects.create(
            entry=self.published,
            author=self.author,
            rating=4,
            body="The first review is valid and should be stored.",
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Review.objects.create(
                    entry=self.published,
                    author=self.author,
                    rating=5,
                    body="A duplicate review must be rejected by the database.",
                )

    def test_deleting_author_keeps_entry(self):
        self.author.delete()
        self.published.refresh_from_db()
        self.assertIsNone(self.published.created_by)
