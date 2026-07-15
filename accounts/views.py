from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import CurrentUserSerializer, SentryVisionTokenObtainPairSerializer


class SentryVisionTokenObtainPairView(TokenObtainPairView):
    serializer_class = SentryVisionTokenObtainPairSerializer


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(CurrentUserSerializer(request.user).data)
