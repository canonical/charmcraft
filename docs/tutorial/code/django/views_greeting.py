from django.http import HttpResponse  # ty:ignore[unresolved-import]


def index(request):
    return HttpResponse("Hello, world!\n")
