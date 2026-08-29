"""Transactional catalog operations shared by admin and other callers."""

from __future__ import annotations

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from .models import Entry, Submission


class SubmissionStateError(ValueError):
    """Raised when a reviewed submission is processed again."""


def _require_staff(reviewer) -> None:
    if not reviewer.is_active or not reviewer.is_staff:
        raise PermissionDenied("Staff permission is required to moderate submissions.")


def _entry_slug(submission: Submission) -> str:
    base = slugify(submission.title) or "entry"
    return f"{base}-{submission.pk}"


# [Implementation 12]
# The row is locked before checking its state so two staff requests cannot approve it independently.
@transaction.atomic
def approve_submission(
    *,
    submission_id: int,
    reviewer,
    note: str = "",
) -> Entry:
    _require_staff(reviewer)
    submission = Submission.objects.select_for_update().get(pk=submission_id)
    if submission.status != Submission.Status.PENDING:
        raise SubmissionStateError("Only pending submissions can be approved.")

    entry = Entry.objects.create(
        title=submission.title,
        slug=_entry_slug(submission),
        summary=submission.summary,
        description=(
            f"Source: {submission.source_url}" if submission.source_url else submission.summary
        ),
        category=_default_category(),
        status=Entry.Status.DRAFT,
        created_by=reviewer,
    )

    submission.status = Submission.Status.APPROVED
    submission.moderation_note = note.strip()
    submission.reviewed_by = reviewer
    submission.reviewed_at = timezone.now()
    submission.created_entry = entry
    submission.save(
        update_fields=(
            "status",
            "moderation_note",
            "reviewed_by",
            "reviewed_at",
            "created_entry",
            "updated_at",
        )
    )
    return entry


@transaction.atomic
def reject_submission(
    *,
    submission_id: int,
    reviewer,
    note: str = "",
) -> Submission:
    _require_staff(reviewer)
    submission = Submission.objects.select_for_update().get(pk=submission_id)
    if submission.status != Submission.Status.PENDING:
        raise SubmissionStateError("Only pending submissions can be rejected.")

    submission.status = Submission.Status.REJECTED
    submission.moderation_note = note.strip()
    submission.reviewed_by = reviewer
    submission.reviewed_at = timezone.now()
    submission.save(
        update_fields=(
            "status",
            "moderation_note",
            "reviewed_by",
            "reviewed_at",
            "updated_at",
        )
    )
    return submission


def _default_category():
    from .models import Category

    category, _ = Category.objects.get_or_create(
        slug="unclassified",
        defaults={
            "name": "Unclassified",
            "description": "Items created from approved submissions before classification.",
        },
    )
    return category
