from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    # TODO: obfuscate recording IDs
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
]
