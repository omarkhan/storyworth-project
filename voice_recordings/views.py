import re

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.templatetags.static import static
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse

from .models import Recording

PHONE_NUMBER_PATTERN = "[0-9]{3}-?[0-9]{3}-?[0-9]{4}"


@require_http_methods(["GET", "POST"])
def form(request):
    if request.method == "POST":
        tel = request.POST["tel"]
        recording = Recording.objects.create(phone_number=tel)
        call_started_webhook_path = reverse("call_started_webhook", args=[recording.pk])
        call_started_webhook_url = request.build_absolute_uri(call_started_webhook_path)

        # FIXME: this will error out and return a 500 response for invalid
        # phone numbers. We should show a helpful error message instead.
        # FIXME(performance): 3rd party API call in response handler. Move to background job
        recording.twilio_call_sid = _place_call(
            tel, webhook_url=call_started_webhook_url
        )
        recording.save()

        return redirect("recording", recording.pk)

    return render(
        request,
        "voice_recordings/form.html",
        {"phone_number_pattern": PHONE_NUMBER_PATTERN},
    )


@require_GET
def recording(request, recording_id: int):
    recording = Recording.objects.get(pk=recording_id)
    return render(request, "voice_recordings/recording.html", {"recording": recording})


@require_http_methods(["GET", "POST"])
@csrf_exempt
def call_started_webhook(request, recording_id: int):
    # TODO(security): verify that request comes from Twilio
    response = VoiceResponse()

    greeting_path = static("voice_recordings/greeting.aifc")
    greeting_url = request.build_absolute_uri(greeting_path)
    response.play(greeting_url)

    recording_status_updated_webhook_path = reverse(
        "recording_status_updated_webhook",
        args=[recording_id],
    )
    recording_status_updated_webhook_url = request.build_absolute_uri(
        recording_status_updated_webhook_path
    )
    response.record(
        recording_status_callback=recording_status_updated_webhook_url,
        trim="trim-silence",
    )

    return HttpResponse(str(response), content_type="application/xml")


@require_http_methods(["GET", "POST"])
@csrf_exempt
def recording_status_updated_webhook(request, recording_id: int):
    # Twilio sometimes sends webhook requests as GET, and sometimes as POST.
    # TODO: figure out how to get Twilio to use a consistent HTTP method.
    if request.method == "GET":
        params = request.GET
    else:
        params = request.POST

    if params["RecordingStatus"] == "completed":
        recording = Recording.objects.get(pk=recording_id)
        recording.status = Recording.Status.COMPLETE
        recording.twilio_recording_sid = params["RecordingSid"]
        recording.save()
        # TODO: broadcast to UI

    return HttpResponse(status=200)


@require_GET
def recording_status(request, recording_id: int):
    recording = Recording.objects.get(pk=recording_id)
    return HttpResponse(recording.status, content_type="text/plain")


def _place_call(tel: str, webhook_url: str) -> str:
    twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    call = twilio_client.calls.create(
        to=_normalize_phone_number(tel),
        from_=settings.TWILIO_FROM_NUMBER,
        url=webhook_url,
    )
    return call.sid


def _normalize_phone_number(tel: str) -> str:
    assert re.fullmatch(PHONE_NUMBER_PATTERN, tel)
    without_dashes = tel.replace("-", "")
    return f"+1{without_dashes}"  # US numbers only for now
