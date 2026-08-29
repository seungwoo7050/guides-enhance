from unittest.mock import patch

from django.core.exceptions import PermissionDenied
from django.test import TestCase

from catalog.models import Entry, Submission
from catalog.services import SubmissionStateError, approve_submission, reject_submission

from .base import CatalogTestDataMixin


class SubmissionModerationTests(CatalogTestDataMixin, TestCase):
    def create_submission(self):
        return Submission.objects.create(
            title="Suggested Entry",
            summary="A submitted summary that is ready for staff review.",
            source_url="https://example.com/reference",
            submitted_by=self.author,
        )

    def test_staff_approval_creates_one_draft_and_records_review(self):
        submission = self.create_submission()
        entry = approve_submission(submission_id=submission.pk, reviewer=self.staff)

        submission.refresh_from_db()
        self.assertEqual(entry.status, Entry.Status.DRAFT)
        self.assertEqual(submission.status, Submission.Status.APPROVED)
        self.assertEqual(submission.created_entry, entry)
        self.assertEqual(submission.reviewed_by, self.staff)
        self.assertIsNotNone(submission.reviewed_at)

    def test_submission_cannot_be_approved_twice(self):
        submission = self.create_submission()
        approve_submission(submission_id=submission.pk, reviewer=self.staff)

        with self.assertRaises(SubmissionStateError):
            approve_submission(submission_id=submission.pk, reviewer=self.staff)

        self.assertEqual(Entry.objects.filter(source_submission=submission).count(), 1)

    def test_non_staff_user_cannot_moderate(self):
        submission = self.create_submission()
        with self.assertRaises(PermissionDenied):
            approve_submission(submission_id=submission.pk, reviewer=self.author)

    def test_rejection_records_reviewer_without_creating_entry(self):
        submission = self.create_submission()
        reject_submission(
            submission_id=submission.pk,
            reviewer=self.staff,
            note="Insufficient source information",
        )
        submission.refresh_from_db()
        self.assertEqual(submission.status, Submission.Status.REJECTED)
        self.assertEqual(submission.reviewed_by, self.staff)
        self.assertIsNone(submission.created_entry)
        self.assertEqual(submission.moderation_note, "Insufficient source information")

    def test_approval_rolls_back_when_entry_creation_fails(self):
        submission = self.create_submission()
        with patch("catalog.services._default_category", side_effect=RuntimeError("write failed")):
            with self.assertRaises(RuntimeError):
                approve_submission(submission_id=submission.pk, reviewer=self.staff)

        submission.refresh_from_db()
        self.assertEqual(submission.status, Submission.Status.PENDING)
        self.assertIsNone(submission.reviewed_by)
