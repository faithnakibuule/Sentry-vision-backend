from django.contrib import admin

from .models import PersonOfInterest


@admin.register(PersonOfInterest)
class PersonOfInterestAdmin(admin.ModelAdmin):
    list_display = ("full_name", "threat_level", "has_encoding", "created_at")
    list_filter = ("threat_level",)
    search_fields = ("full_name", "notes")
    readonly_fields = ("face_encoding", "created_at", "updated_at")

    @admin.display(boolean=True)
    def has_encoding(self, obj):
        return bool(obj.face_encoding)
