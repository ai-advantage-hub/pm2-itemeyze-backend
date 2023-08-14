from django.urls import path

from custom_admin import views

urlpatterns = [

    # Onboarding
    # path("signup", views.SignUpViewSet.as_view(
    #     {"post": "create"}), name="signup"),
    path("login", views.AdminLoginView.as_view({"post": "create"}), name="login"),
    path("reset_password", views.AdminResetPasswordView.as_view({"post": "create"}), name="reset_password"),
    path("Terms_and_condition", views.TermsandconditionView.as_view({"get": "create"}), name="Terms_and_condition"),
    path("CompanyNameView", views.CompanyNameView.as_view({"get": "create"}), name="CompanyNameView"),
    path("Adminprofile", views.AdminprofileView.as_view({"get": "create"}), name="Adminprofile"),
    path("AdminprofileUpdate", views.AdminprofileUpdateView.as_view({"get": "create"}), name="AdminprofileUpdate")


]