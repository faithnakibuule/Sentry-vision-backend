import io
import numpy as np
from PIL import Image
import face_recognition

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
        Uploads a new angled reference image for a specific person
        and automatically computes its 128D facial encoding.
        Endpoint: POST /api/persons/{id}/upload_angle/
        """
        person = self.get_object()
        
        # 1. Validate 'image' key exists
        if 'image' not in request.FILES:
            return Response(
                {"error": "No image uploaded. Expected key 'image'."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        uploaded_file = request.FILES['image']

        # 2. Extract facial encoding directly in-memory
        try:
            image_bytes = uploaded_file.read()
            pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            
            # Downscale large mobile uploads (speeds up encoding drastically)
            pil_image.thumbnail((1024, 1024))
            
            image_np = np.array(pil_image)

            # Detect face
            face_locations = face_recognition.face_locations(image_np, model="hog")

            if len(face_locations) == 0:
                return Response(
                    {"error": "No face detected in the uploaded image."}, 
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY
                )
            elif len(face_locations) > 1:
                return Response(
                    {"error": "Multiple faces detected. Please upload an image with only one face."}, 
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY
                )

            # Generate 128-d encoding array
            encodings = face_recognition.face_encodings(image_np, known_face_locations=face_locations)
            encoding_list = encodings[0].tolist()

            # Reset file read pointer so Django can save the image file properly
            uploaded_file.seek(0)

        except Exception as e:
            return Response(
                {"error": f"Facial encoding error: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 3. Save Image & Encoding using Serializer
        data = request.data.copy()
        serializer = PersonImageSerializer(data=data)

        if serializer.is_valid():
            # Pass the calculated encoding directly into save()
            serializer.save(person=person, encoding=encoding_list)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)