import importlib

import pytest
from django.apps import apps as django_apps
from django.conf import settings

from plane.db.models import Cycle, Project, User, Workspace

migration = importlib.import_module("plane.db.migrations.0125_default_timezone_ist")


def test_model_defaults_follow_setting():
    tz = settings.DEFAULT_TIMEZONE
    assert Workspace._meta.get_field("timezone").default == tz
    assert Project._meta.get_field("timezone").default == tz
    assert Cycle._meta.get_field("timezone").default == tz
    assert User._meta.get_field("user_timezone").default == tz


@pytest.mark.django_db
def test_data_migration_round_trip():
    utc = User.objects.create(email="utc@x.io", username="utc", user_timezone="UTC")
    other = User.objects.create(email="ny@x.io", username="ny", user_timezone="America/New_York")
    migration.forwards(django_apps, None)
    utc.refresh_from_db()
    other.refresh_from_db()
    assert (utc.user_timezone, other.user_timezone) == (settings.DEFAULT_TIMEZONE, "America/New_York")
    migration.backwards(django_apps, None)
    utc.refresh_from_db()
    assert utc.user_timezone == "UTC"
