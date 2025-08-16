from django.urls import path

from . import views

urlpatterns = [
    path("", views.form, name="form"),
    # FIXME: Including integer primary keys in the URL is not ideal.
    # - Gives a sense of many recordings we have
    # - Makes it too easy to guess the URL of someone else's recording
    #
    # Use an obfuscated identifier instead, like a UUID.
    path("recording/<int:recording_id>/", views.recording, name="recording"),
    path(
        "recording/<int:recording_id>/call_started/",
        views.call_started_webhook,
        name="call_started_webhook",
    ),
    path(
        "recording/<int:recording_id>/recording_status_updated/",
        views.recording_status_updated_webhook,
        name="recording_status_updated_webhook",
    ),
    path(
        "recording/<int:recording_id>/status/",
        views.recording_status,
        name="recording_status",
    ),
]
