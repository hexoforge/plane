import importlib

import pytest
from django.apps import apps as django_apps

from plane.db.models import Cycle, Project, User, Workspace

migration = importlib.import_module("plane.db.migrations.0125_default_timezone_ist")


def test_model_defaults_are_ist():
    assert Workspace._meta.get_field("timezone").default == "Asia/Kolkata"
    assert Project._meta.get_field("timezone").default == "Asia/Kolkata"
    assert Cycle._meta.get_field("timezone").default == "Asia/Kolkata"
    assert User._meta.get_field("user_timezone").default == "Asia/Kolkata"


@pytest.mark.django_db
def test_data_migration_round_trip():
    utc = User.objects.create(email="utc@x.io", username="utc", user_timezone="UTC")
    other = User.objects.create(email="ny@x.io", username="ny", user_timezone="America/New_York")
    migration.forwards(django_apps, None)
    utc.refresh_from_db()
    other.refresh_from_db()
    assert (utc.user_timezone, other.user_timezone) == ("Asia/Kolkata", "America/New_York")
    migration.backwards(django_apps, None)
    utc.refresh_from_db()
    assert utc.user_timezone == "UTC"
