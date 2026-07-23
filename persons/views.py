from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response

from accounts.permissions import IsAdminOrReadOnlyRole

from .models import PersonImage, PersonOfInterest
from .serializers import PersonImageSerializer, PersonOfInterestSerializer


class PersonOfInterestViewSet(viewsets.ModelViewSet):
    queryset = PersonOfInterest.objects.all()
    serializer_class = PersonOfInterestSerializer
    permission_classes = [IsAdminOrReadOnlyRole]

    @action(
        detail=True, 
        methods=["post"], 
        parser_classes=[MultiPartParser, FormParser]
    )
    def upload_angle(self, request, pk=None):
        """
        Uploads a new angled reference image for a specific person.
        Endpoint: POST /api/persons/{id}/upload_angle/
        """
        person = self.get_object()
        
        # Attach the person context to the incoming data
        data = request.data.copy()
        
        serializer = PersonImageSerializer(data=data)
        if serializer.is_valid():
            # Save the image instance and link it to the current person
            serializer.save(person=person)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)