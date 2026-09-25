import os

from django.http import HttpResponse


def index(request):
    return HttpResponse(f"{os.environ.get('DJANGO_GREETING', 'Hello, world!')}\n")
