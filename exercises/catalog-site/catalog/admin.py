"""Admin configuration and moderation actions."""

from django.contrib import admin, messages
from django.utils import timezone

from .models import Category, Entry, Review, Submission, Tag
from .services import SubmissionStateError, approve_submission, reject_submission


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "status", "published_at", "updated_at")
    list_filter = ("status", "category", "tags")
    search_fields = ("title", "summary", "description")
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("tags",)
    actions = ("publish_entries", "move_to_draft")

    @admin.action(description="Publish selected entries")
    def publish_entries(self, request, queryset):
        updated = queryset.update(status=Entry.Status.PUBLISHED, published_at=timezone.now())
        self.message_user(request, f"Published {updated} entries.", messages.SUCCESS)

    @admin.action(description="Move selected entries to draft")
    def move_to_draft(self, request, queryset):
        updated = queryset.update(status=Entry.Status.DRAFT, published_at=None)
        self.message_user(request, f"Moved {updated} entries to draft.", messages.SUCCESS)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("entry", "author", "rating", "is_visible", "created_at")
    list_filter = ("rating", "is_visible")
    search_fields = ("entry__title", "author__username", "body")
    list_select_related = ("entry", "author")


# [Implementation 13]
# Admin actions call the same transactional services used by any future moderation entrypoint.
@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("title", "submitted_by", "status", "reviewed_by", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("title", "summary", "submitted_by__username")
    readonly_fields = ("reviewed_by", "reviewed_at", "created_entry", "created_at", "updated_at")
    list_select_related = ("submitted_by", "reviewed_by", "created_entry")
    actions = ("approve_selected", "reject_selected")

    @admin.action(description="Approve selected submissions")
    def approve_selected(self, request, queryset):
        approved = 0
        skipped = 0
        for submission_id in queryset.values_list("pk", flat=True):
            try:
                approve_submission(submission_id=submission_id, reviewer=request.user)
            except SubmissionStateError:
                skipped += 1
            else:
                approved += 1
        self.message_user(
            request,
            f"Approved {approved} submissions; skipped {skipped} already reviewed submissions.",
            messages.SUCCESS if approved else messages.WARNING,
        )

    @admin.action(description="Reject selected submissions")
    def reject_selected(self, request, queryset):
        rejected = 0
        skipped = 0
        for submission_id in queryset.values_list("pk", flat=True):
            try:
                reject_submission(submission_id=submission_id, reviewer=request.user)
            except SubmissionStateError:
                skipped += 1
            else:
                rejected += 1
        self.message_user(
            request,
            f"Rejected {rejected} submissions; skipped {skipped} already reviewed submissions.",
            messages.SUCCESS if rejected else messages.WARNING,
        )
