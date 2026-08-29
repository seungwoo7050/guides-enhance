"""Local development settings."""

from .base import *  # noqa: F403

SECRET_KEY = "development-only-secret-key-do-not-use-in-production"
DEBUG = True
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver"]
