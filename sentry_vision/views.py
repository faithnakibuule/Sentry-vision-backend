from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView


class AuthenticatedMediaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, path):
        media_root = Path(settings.MEDIA_ROOT).resolve()
        requested = (media_root / path).resolve()
        if media_root not in requested.parents and requested != media_root:
            raise Http404
        if not requested.exists() or not requested.is_file():
            raise Http404
        return FileResponse(open(requested, "rb"))
