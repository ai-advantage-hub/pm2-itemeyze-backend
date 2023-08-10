from django.urls import path

from users import views

urlpatterns = [

    # Onboarding
    path("signup", views.SignUpViewSet.as_view(
        {"post": "create"}), name="signup"),
]