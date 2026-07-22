from rest_framework import serializers

from .models import PersonImage, PersonOfInterest
from .services import get_face_encoding


class PersonImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PersonImage
        fields = (
            "id",
            "photo",
            "angle_label",
            "created_at",
        )
        read_only_fields = ("created_at",)

    def validate_photo(self, photo):
        encoding = get_face_encoding(photo)
        try:
            photo.seek(0)
        except (AttributeError, ValueError):
            pass
        if encoding is None:
            raise serializers.ValidationError(
                "No face was detected in this angled photo."
            )
        return photo


class PersonOfInterestSerializer(serializers.ModelSerializer):
    additional_images = PersonImageSerializer(many=True, read_only=True)

    class Meta:
        model = PersonOfInterest
        fields = (
            "id",
            "full_name",
            "photo",
            "threat_level",
            "notes",
            "additional_images",
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