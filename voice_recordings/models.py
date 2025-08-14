from typing import Optional

from django.conf import settings
from django.db import models


class Recording(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = "IN_PROGRESS"
        COMPLETE = "COMPLETE"
        FAILED = "FAILED"

    created_at = models.DateTimeField(auto_now_add=True)
    phone_number = models.CharField(max_length=100)
    twilio_call_sid = models.CharField(blank=True, max_length=100)
    twilio_recording_sid = models.CharField(blank=True, max_length=100)
    status = models.CharField(
        choices=Status,
        default=Status.IN_PROGRESS,
        max_length=100,
    )

    @property
    def twilio_recording_url(self) -> Optional[str]:
        if self.status != self.Status.COMPLETE:
            return None

        return f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Recordings/{self.twilio_recording_sid}.mp3"
