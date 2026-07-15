from django.urls import path

from .views import CurrentUserView, SentryVisionTokenObtainPairView

urlpatterns = [
    path("auth/login/", SentryVisionTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/me/", CurrentUserView.as_view(), name="auth-me"),
]
