import time

import pytest

from voice_recordings.models import Recording


@pytest.mark.django_db
def test_happy_path_browser_with_polling(page, live_server, monkeypatch, settings):
    """
    Playwright browser E2E happy path using the template's JS polling:
    1. User opens form
    2. Fills phone number & submits
    3. Background: Mark recording COMPLETE after JS polling starts
    4. Browser auto-refreshes & shows 'Recording complete!'
    """

    # --- Monkeypatch Twilio Client ---
    class DummyCall:
        sid = "FAKE_CALL_SID"

    class DummyCalls:
        def create(self, to, from_, url):
            assert to.startswith("+1")
            assert from_ == settings.TWILIO_FROM_NUMBER
            assert url.startswith("http")
            return DummyCall()

    class DummyClient:
        def __init__(self, sid, token):
            assert sid == settings.TWILIO_ACCOUNT_SID
            assert token == settings.TWILIO_AUTH_TOKEN
            self.calls = DummyCalls()

    monkeypatch.setattr("voice_recordings.views.Client", DummyClient)

    # --- Step 1: Visit form page ---
    page.goto(f"{live_server.url}")
    assert page.locator('button:has-text("Call me now")').is_visible()

    # --- Step 2: Fill in phone number & submit ---
    tel = "123-456-7890"
    page.fill('input[name="tel"]', tel)
    page.click('button:has-text("Call me now")')

    # Grab the created Recording instance
    recording = Recording.objects.first()
    assert recording is not None
    assert recording.status == Recording.Status.IN_PROGRESS

    # --- Step 3: Wait until polling script is likely active ---
    # The script waits 10s before the first poll, so we mark COMPLETE after ~3s
    time.sleep(3)
    recording.status = Recording.Status.COMPLETE
    recording.save()

    # --- Step 4: Browser should detect change & auto-reload ---
    # Polling delay: script waits 10s + server round-trip
    page.wait_for_selector("text=Recording complete!", timeout=15000)
    assert "Recording complete!" in page.content()
