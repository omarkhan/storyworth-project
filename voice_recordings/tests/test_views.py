import pytest
from django.urls import reverse

from voice_recordings.models import Recording


def test_form_get(client):
    url = reverse("form")
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_form_post_places_call(monkeypatch, client, settings):
    # Monkeypatch Twilio Client.calls.create to avoid network calls
    fake_sid = "FAKE_CALL_SID"
    tel = "123-456-7890"

    class DummyCall:
        sid = fake_sid

    class DummyCalls:
        def create(self, to, from_, url):
            # Check that number is normalized
            assert to == "+11234567890"
            assert from_ == settings.TWILIO_FROM_NUMBER
            assert url.startswith("http")
            return DummyCall()

    class DummyClient:
        def __init__(self, sid, token):
            assert sid == settings.TWILIO_ACCOUNT_SID
            assert token == settings.TWILIO_AUTH_TOKEN
            self.calls = DummyCalls()

    monkeypatch.setattr("voice_recordings.views.Client", DummyClient)

    # Create POST request
    url = reverse("form")
    response = client.post(url, {"tel": tel})

    # Redirect to recording page
    recording = Recording.objects.first()
    assert response.status_code == 302
    assert response.url == reverse("recording", args=[recording.pk])

    # DB saved
    assert recording.phone_number == tel
    assert recording.twilio_call_sid == fake_sid


@pytest.mark.django_db
def test_recording_get(client):
    rec = Recording.objects.create(phone_number="1234567890")
    url = reverse("recording", args=[rec.pk])
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_call_started_webhook_generates_twiml(client):
    rec = Recording.objects.create(phone_number="1234567890")
    url = reverse("call_started_webhook", args=[rec.pk])
    response = client.post(url)
    assert response.status_code == 200
    assert response["Content-Type"] == "application/xml"
    body = response.content.decode()
    assert "<Play>" in body
    assert "<Record" in body


@pytest.mark.django_db
def test_recording_status_updated_webhook_get_updates_recording(client):
    rec = Recording.objects.create(phone_number="1234567890")
    url = reverse("recording_status_updated_webhook", args=[rec.pk])
    params = {"RecordingStatus": "completed", "RecordingSid": "RS12345"}
    response = client.get(url, params)
    rec.refresh_from_db()
    assert response.status_code == 200
    assert rec.status == Recording.Status.COMPLETE
    assert rec.twilio_recording_sid == "RS12345"


@pytest.mark.django_db
def test_recording_status_updated_webhook_post_noop(client):
    rec = Recording.objects.create(phone_number="1234567890")
    url = reverse("recording_status_updated_webhook", args=[rec.pk])
    # Status is not 'completed', so it should not change
    response = client.post(url, {"RecordingStatus": "in-progress"})
    rec.refresh_from_db()
    assert response.status_code == 200
    assert rec.status != Recording.Status.COMPLETE


@pytest.mark.django_db
def test_recording_status_view(client):
    rec = Recording.objects.create(
        phone_number="1234567890", status=Recording.Status.COMPLETE
    )
    url = reverse("recording_status", args=[rec.pk])
    response = client.get(url)
    assert response.status_code == 200
    assert response["Content-Type"] == "text/plain"
    assert response.content.decode() == Recording.Status.COMPLETE
