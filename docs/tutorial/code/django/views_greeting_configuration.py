import os

from django.http import HttpResponse  # ty:ignore[unresolved-import]


def index(request):
    return HttpResponse(f"{os.environ.get('DJANGO_GREETING', 'Hello, world!')}\n")
