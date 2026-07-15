from rest_framework import viewsets

from accounts.permissions import IsAdminOrReadOnlyRole

from .models import PersonOfInterest
from .serializers import PersonOfInterestSerializer


class PersonOfInterestViewSet(viewsets.ModelViewSet):
    queryset = PersonOfInterest.objects.all()
    serializer_class = PersonOfInterestSerializer
    permission_classes = [IsAdminOrReadOnlyRole]
