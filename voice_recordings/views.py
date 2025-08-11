from django.shortcuts import render


def index(request):
    return render(request, "voice_recordings/index.html")
