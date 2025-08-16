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
    """
    On GET, display a form allowing the user to input their phone number.

    On POST, create a Recording instance in our database. Then call the number
    and redirect to the recording page.
    """
    if request.method == "POST":
        tel = request.POST["tel"]
        recording = Recording.objects.create(phone_number=tel)

        # Place a call to the given number using the Twilio API. When the call
        # connects, Twilio will send us a webhook request to a url of our
        # choosing. Send a webhook url scoped to this recording:
        call_started_webhook_path = reverse("call_started_webhook", args=[recording.pk])
        call_started_webhook_url = request.build_absolute_uri(call_started_webhook_path)

        # FIXME: This will error out and return a 500 response for invalid
        # phone numbers. We should show a helpful error message instead.
        # FIXME(performance): 3rd party API call in response handler. Move to
        # background job.
        # FIXME: Twilio outbound voice calls are rate-limited to 1/sec. After
        # moving this Twilio API call to a background job, throttle the job
        # queue to stay within the rate-limit. Monitor the queue, and set up an
        # alert if it starts growing so we know to add more capacity -
        # additional Twilio accounts, perhaps?
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
    # FIXME: Recordings are currently publicly available. We can't restrict
    # this view to logged in users only if we want to allow unauthenticated
    # users play back their own recordings. On the other hand, we don't want to
    # allow anyone on the internet to listen to other people's recordings!
    #
    # This risk is mitigated somewhat if we serve this recording page via
    # private url that the storyteller shares directly with the person
    # recording their story (still TODO). There is still a privacy risk however
    # as long as recordings remain available over the public internet.
    #
    # One possible solution would be to only allow a completed recording to be
    # opened *once* by an unauthenticated user. This will almost certainly be
    # the user recording the story, since they are redirected to the recording
    # page when they request a call. As an additional safeguard, we can lock
    # recordings down after a certain amount of time. This strikes me as a good
    # balance between privacy (not letting other people listen to my recording)
    # and convenience (being able play my recording back without creating an
    # account).
    recording = Recording.objects.get(pk=recording_id)
    return render(request, "voice_recordings/recording.html", {"recording": recording})


@require_http_methods(["GET", "POST"])
@csrf_exempt
def call_started_webhook(request, recording_id: int):
    """
    Webhook handler called by Twilio when a call starts. Respond with TwiML
    (Twilio's xml-based instruction format) telling Twilio to:

    1. Play a greeting.
    2. Record the rest of the call.
    """
    # TODO(security): verify that request comes from Twilio
    response = VoiceResponse()

    greeting_path = static("voice_recordings/greeting.aifc")
    greeting_url = request.build_absolute_uri(greeting_path)
    response.play(greeting_url)

    # Ask Twilio to send recording status updates to the following webhook
    # endpoint, scoped to this recording:
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
    """
    Webhook handler called by Twilio when a recording's status changes.

    If Twilio tells us the recording is complete, update the corresponding
    Recording instance in our database.
    """
    # TODO(security): verify that request comes from Twilio

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

    # TODO: handle other statuses (failed, etc.)

    return HttpResponse(status=200)


@require_GET
def recording_status(request, recording_id: int):
    """
    Return the given Recording instance's status as plain text. The frontend
    polls this endpoint to check if the recording is finished.
    """
    # FIXME: Polling introduces some latency on the frontend, and cause sharp
    # increases in traffic. Implement this using server-sent events or
    # websockets instead, for performance and better UX.
    recording = Recording.objects.get(pk=recording_id)
    return HttpResponse(recording.status, content_type="text/plain")


def _place_call(tel: str, webhook_url: str) -> str:
    """
    Using the Twilio Voice API, place a call to the given number. Return the
    call's Twilio SID.
    """
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
