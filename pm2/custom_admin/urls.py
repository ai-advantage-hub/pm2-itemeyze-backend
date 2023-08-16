from django.urls import path

from custom_admin import views

urlpatterns = [

    # Onboarding
    path("login", views.AdminLoginView.as_view({"post": "create"}), name="login"),

    #Admin profile
    path("Adminprofile", views.AdminProfileViewSet.as_view({"get": "list"}), name="Adminprofile"),
    path("AdminprofileUpdate", views.AdminProfileViewSet.as_view({"put": "update"}), name="AdminprofileUpdate"),
    path("reset_password", views.AdminProfileViewSet.as_view({"put": "create"}), name="reset_password"),

    #Content Management
    path("Terms_and_condition", views.ContentManagementViewSet.as_view({"get": "list"}), name="Terms_and_condition"),
    path("update_content", views.ContentManagementViewSet.as_view({"put": "update"}), name="update_content"),
    path("delete_content", views.ContentManagementViewSet.as_view({"delete": "delete"}), name="delete_content"),

    path("CompanyNameView", views.CompanyNameView.as_view({"get": "create"}), name="CompanyNameView"),
    # path("Adminprofile", views.AdminProfileViewSet.as_view({"get": "list"}), name="Adminprofile"),
    # path("AdminprofileUpdate", views.AdminProfileViewSet.as_view({"get": "update"}), name="AdminprofileUpdate")


]