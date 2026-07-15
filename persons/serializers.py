from rest_framework import serializers

from .models import PersonOfInterest
from .services import get_face_encoding


class PersonOfInterestSerializer(serializers.ModelSerializer):
    class Meta:
        model = PersonOfInterest
        fields = (
            "id",
            "full_name",
            "photo",
            "threat_level",
            "notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")

    def validate_photo(self, photo):
        encoding = get_face_encoding(photo)
        try:
            photo.seek(0)
        except (AttributeError, ValueError):
            pass
        if encoding is None:
            raise serializers.ValidationError("No face was detected in this photo.")
        return photo
