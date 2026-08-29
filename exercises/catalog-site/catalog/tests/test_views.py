from django.test import TestCase
from django.urls import reverse

from catalog.models import Review, Submission

from .base import CatalogTestDataMixin


class PublicCatalogViewTests(CatalogTestDataMixin, TestCase):
    def test_entry_list_shows_published_entry_only(self):
        response = self.client.get(reverse("catalog:entry-list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.published.title)
        self.assertNotContains(response, self.draft.title)

    def test_draft_detail_returns_not_found(self):
        response = self.client.get(
            reverse("catalog:entry-detail", kwargs={"slug": self.draft.slug})
        )
        self.assertEqual(response.status_code, 404)

    def test_search_parameter_is_applied(self):
        response = self.client.get(reverse("catalog:entry-list"), {"q": "Published"})
        self.assertContains(response, self.published.title)


class ReviewViewTests(CatalogTestDataMixin, TestCase):
    def review_create_url(self):
        return reverse("catalog:review-create", kwargs={"slug": self.published.slug})

    def test_login_is_required_to_create_review(self):
        response = self.client.get(self.review_create_url())
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_review_is_saved_with_request_user_and_entry(self):
        self.client.force_login(self.author)
        response = self.client.post(
            self.review_create_url(),
            {"rating": 5, "body": "A detailed review that passes validation."},
        )
        self.assertRedirects(response, self.published.get_absolute_url())
        review = Review.objects.get()
        self.assertEqual(review.author, self.author)
        self.assertEqual(review.entry, self.published)

    def test_second_review_returns_form_error(self):
        Review.objects.create(
            entry=self.published,
            author=self.author,
            rating=4,
            body="The first valid review remains stored.",
        )
        self.client.force_login(self.author)
        response = self.client.post(
            self.review_create_url(),
            {"rating": 5, "body": "A second valid-looking review must be rejected."},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "이미 후기를 작성했습니다")
        self.assertEqual(Review.objects.count(), 1)

    def test_other_user_cannot_edit_review(self):
        review = Review.objects.create(
            entry=self.published,
            author=self.author,
            rating=4,
            body="Only the author may edit this review.",
        )
        self.client.force_login(self.other_user)
        response = self.client.get(
            reverse(
                "catalog:review-update",
                kwargs={"slug": self.published.slug, "review_pk": review.pk},
            )
        )
        self.assertEqual(response.status_code, 403)

    def test_author_can_edit_review(self):
        review = Review.objects.create(
            entry=self.published,
            author=self.author,
            rating=4,
            body="The original body is long enough.",
        )
        self.client.force_login(self.author)
        response = self.client.post(
            reverse(
                "catalog:review-update",
                kwargs={"slug": self.published.slug, "review_pk": review.pk},
            ),
            {"rating": 5, "body": "The updated body is also long enough."},
        )
        self.assertRedirects(response, self.published.get_absolute_url())
        review.refresh_from_db()
        self.assertEqual(review.rating, 5)

    def test_review_url_must_match_entry_slug(self):
        review = Review.objects.create(
            entry=self.published,
            author=self.author,
            rating=4,
            body="The route must identify the review's actual entry.",
        )
        self.client.force_login(self.author)
        response = self.client.get(
            reverse(
                "catalog:review-update",
                kwargs={"slug": self.draft.slug, "review_pk": review.pk},
            )
        )
        self.assertEqual(response.status_code, 404)


class SubmissionViewTests(CatalogTestDataMixin, TestCase):
    def test_submission_is_saved_for_logged_in_user(self):
        self.client.force_login(self.author)
        response = self.client.post(
            reverse("catalog:submission-create"),
            {
                "title": "New Catalog Entry",
                "summary": "A summary long enough to pass form validation.",
                "source_url": "https://example.com/source",
            },
        )
        self.assertRedirects(response, reverse("catalog:submission-list"))
        self.assertEqual(Submission.objects.get().submitted_by, self.author)

    def test_submission_list_does_not_include_other_users_rows(self):
        Submission.objects.create(
            title="Other user submission",
            summary="This row must not appear in the author's list.",
            submitted_by=self.other_user,
        )
        own = Submission.objects.create(
            title="Own submission",
            summary="This row belongs to the currently logged in author.",
            submitted_by=self.author,
        )
        self.client.force_login(self.author)
        response = self.client.get(reverse("catalog:submission-list"))
        self.assertContains(response, own.title)
        self.assertNotContains(response, "Other user submission")
