from django.test import TestCase
from django.urls import reverse

from catalog.models import Review

from .base import CatalogTestDataMixin


class CatalogApiTests(CatalogTestDataMixin, TestCase):
    def test_list_returns_public_entries_only(self):
        response = self.client.get(reverse("catalog:api-entry-list"))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["results"][0]["slug"], self.published.slug)

    def test_list_reuses_category_filter(self):
        response = self.client.get(
            reverse("catalog:api-entry-list"),
            {"category": self.other_category.slug},
        )
        self.assertEqual(response.json()["results"], [])

    def test_detail_excludes_hidden_reviews(self):
        Review.objects.create(
            entry=self.published,
            author=self.author,
            rating=5,
            body="This visible review should appear in the API response.",
        )
        Review.objects.create(
            entry=self.published,
            author=self.other_user,
            rating=1,
            body="This hidden review must not appear in the API response.",
            is_visible=False,
        )
        response = self.client.get(
            reverse("catalog:api-entry-detail", kwargs={"slug": self.published.slug})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["reviews"]), 1)
        self.assertEqual(response.json()["reviews"][0]["rating"], 5)

    def test_draft_detail_returns_not_found(self):
        response = self.client.get(
            reverse("catalog:api-entry-detail", kwargs={"slug": self.draft.slug})
        )
        self.assertEqual(response.status_code, 404)
