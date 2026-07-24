from django.contrib import admin
from django.utils.html import format_html
from .models import PersonImage, PersonOfInterest


class PersonImageInline(admin.TabularInline):
    model = PersonImage
    extra = 1
    fields = ("photo", "photo_preview", "angle_label", "has_encoding", "created_at")
    readonly_fields = ("photo_preview", "has_encoding", "created_at")

    @admin.display(boolean=True, description="Encoded")
    def has_encoding(self, obj):
        return bool(obj.face_encoding)

    @admin.display(description="Preview")
    def photo_preview(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" style="max-height: 80px; max-width: 80px; border-radius: 6px; object-fit: cover;" />',
                obj.photo.url,
            )
        return "No Image"


@admin.register(PersonOfInterest)
class PersonOfInterestAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "threat_level",
        "has_encoding",
        "additional_images_count",
        "created_at",
    )
    list_filter = ("threat_level",)
    search_fields = ("full_name", "notes")

    # Add photo_preview to readonly fields and explicitly set fieldsets or fields layout
    readonly_fields = ("photo_preview", "face_encoding", "created_at", "updated_at")
    
    # Organizes the detail view form nicely
    fields = (
        "full_name",
        "photo",
        "photo_preview",
        "threat_level",
        "notes",
        "created_at",
        "updated_at",
    )
    
    inlines = [PersonImageInline]

    @admin.display(boolean=True, description="Primary Encoded")
    def has_encoding(self, obj):
        return bool(obj.face_encoding)

    @admin.display(description="Angled Photos")
    def additional_images_count(self, obj):
        return obj.additional_images.count()

    @admin.display(description="Current Primary Photo")
    def photo_preview(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" style="max-height: 160px; max-width: 160px; border-radius: 8px; border: 1px solid #444;" />',
                obj.photo.url,
            )
        return "No Primary Photo Uploaded"


@admin.register(PersonImage)
class PersonImageAdmin(admin.ModelAdmin):
    list_display = ("person", "angle_label", "photo_preview", "has_encoding", "created_at")
    list_filter = ("angle_label", "created_at")
    search_fields = ("person__full_name", "angle_label")
    readonly_fields = ("photo_preview", "face_encoding", "created_at")

    @admin.display(boolean=True, description="Encoded")
    def has_encoding(self, obj):
        return bool(obj.face_encoding)

    @admin.display(description="Preview")
    def photo_preview(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" style="max-height: 60px; max-width: 60px; border-radius: 4px;" />',
                obj.photo.url,
            )
        return "No Image"