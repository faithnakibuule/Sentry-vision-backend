from django.contrib import admin
from .models import PersonImage, PersonOfInterest


class PersonImageInline(admin.TabularInline):
    model = PersonImage
    extra = 1
    fields = ("photo", "angle_label", "has_encoding", "created_at")
    readonly_fields = ("has_encoding", "created_at")

    @admin.display(boolean=True, description="Encoded")
    def has_encoding(self, obj):
        return bool(obj.face_encoding)


@admin.register(PersonOfInterest)
class PersonOfInterestAdmin(admin.ModelAdmin):
    list_display = ("full_name", "threat_level", "has_encoding", "additional_images_count", "created_at")
    list_filter = ("threat_level",)
    search_fields = ("full_name", "notes")
    readonly_fields = ("face_encoding", "created_at", "updated_at")
    inlines = [PersonImageInline]

    @admin.display(boolean=True, description="Primary Encoded")
    def has_encoding(self, obj):
        return bool(obj.face_encoding)

    @admin.display(description="Angled Photos")
    def additional_images_count(self, obj):
        return obj.additional_images.count()


@admin.register(PersonImage)
class PersonImageAdmin(admin.ModelAdmin):
    list_display = ("person", "angle_label", "has_encoding", "created_at")
    list_filter = ("angle_label", "created_at")
    search_fields = ("person__full_name", "angle_label")
    readonly_fields = ("face_encoding", "created_at")

    @admin.display(boolean=True, description="Encoded")
    def has_encoding(self, obj):
        return bool(obj.face_encoding)