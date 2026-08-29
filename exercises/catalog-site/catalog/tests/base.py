from django.contrib.auth import get_user_model
from django.utils import timezone

from catalog.models import Category, Entry, Tag


class CatalogTestDataMixin:
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.author = user_model.objects.create_user(
            username="author",
            email="author@example.com",
            password="test-password-123",
        )
        cls.other_user = user_model.objects.create_user(
            username="other",
            email="other@example.com",
            password="test-password-123",
        )
        cls.staff = user_model.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="test-password-123",
            is_staff=True,
        )
        cls.category = Category.objects.create(name="Games", slug="games")
        cls.other_category = Category.objects.create(name="Travel", slug="travel")
        cls.tag = Tag.objects.create(name="Reference", slug="reference")
        cls.other_tag = Tag.objects.create(name="Community", slug="community")
        cls.published = Entry.objects.create(
            title="Published Entry",
            slug="published-entry",
            summary="A published catalog entry used by tests.",
            description="Published description",
            category=cls.category,
            status=Entry.Status.PUBLISHED,
            created_by=cls.author,
            published_at=timezone.now(),
        )
        cls.published.tags.add(cls.tag)
        cls.draft = Entry.objects.create(
            title="Draft Entry",
            slug="draft-entry",
            summary="A draft that must not appear publicly.",
            description="Draft description",
            category=cls.other_category,
            status=Entry.Status.DRAFT,
            created_by=cls.staff,
        )
        cls.draft.tags.add(cls.other_tag)
