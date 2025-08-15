import os

import pytest
from django.core.management import call_command
from django.test import override_settings

# Needed for Playwright test to run locally.
# TODO: Figure out why we need this and if we can remove it.
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"


@pytest.fixture(scope="session", autouse=True)
def staticfiles(tmp_path_factory):
    """
    Collect static files before running tests.
    """
    static_root = tmp_path_factory.mktemp("static")
    with override_settings(STATIC_ROOT=static_root):
        call_command("collectstatic", "--noinput")
        yield
