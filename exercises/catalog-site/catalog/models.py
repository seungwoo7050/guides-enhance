"""Catalog, review, and submission data models."""

from __future__ import annotations

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse


# [Implementation 2]
# Taxonomy slugs are unique because they are used as stable URL filter values.
class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=80, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ("name",)
        verbose_name_plural = "categories"

    def __str__(self) -> str:
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class EntryQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status=Entry.Status.PUBLISHED)


# [Implementation 3]
# Publication state is stored explicitly so public queries never infer visibility from dates or authors.
class Entry(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"

    title = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True)
    summary = models.CharField(max_length=300)
    description = models.TextField()
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="entries",
    )
    tags = models.ManyToManyField(Tag, related_name="entries", blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="entries",
        blank=True,
        null=True,
    )
    published_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = EntryQuerySet.as_manager()

    class Meta:
        ordering = ("-published_at", "-pk")
        indexes = [
            models.Index(fields=("status", "-published_at"), name="entry_status_published_idx"),
        ]

    def __str__(self) -> str:
        return self.title

    def get_absolute_url(self) -> str:
        return reverse("catalog:entry-detail", kwargs={"slug": self.slug})


# [Implementation 4]
# The database rejects out-of-range ratings and duplicate reviews even when writes bypass ModelForm.
class Review(models.Model):
    entry = models.ForeignKey(Entry, on_delete=models.CASCADE, related_name="reviews")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    body = models.TextField(max_length=2000)
    is_visible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at", "-pk")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(rating__gte=1, rating__lte=5),
                name="review_rating_between_1_and_5",
            ),
            models.UniqueConstraint(
                fields=("entry", "author"),
                name="one_review_per_entry_author",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.entry}: {self.rating}/5 by {self.author}"


# [Implementation 5]
# Moderation records who made the decision and which draft Entry was created from an approved submission.
class Submission(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    title = models.CharField(max_length=160)
    summary = models.CharField(max_length=300)
    source_url = models.URLField(blank=True)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    moderation_note = models.TextField(blank=True, max_length=1000)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="reviewed_submissions",
        blank=True,
        null=True,
    )
    reviewed_at = models.DateTimeField(blank=True, null=True)
    created_entry = models.OneToOneField(
        Entry,
        on_delete=models.SET_NULL,
        related_name="source_submission",
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at", "-pk")
        indexes = [
            models.Index(fields=("submitted_by", "status"), name="submission_user_status_idx"),
        ]

    def __str__(self) -> str:
        return self.title
