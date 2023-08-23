from django.urls import path

from custom_admin import views

urlpatterns = [

    # Onboarding
    path("login", views.AdminLoginView.as_view({"post": "create"}), name="login"),
    path("forgot_password", views.ForgotPasswordViewSet.as_view({"post": "create"}), name="forgot_password"),
    path("ConfirmPassword", views.ResetPasswordViewSet.as_view({"post": "create"}), name="ConfirmPassword"),


    #Admin profile
    path("Adminprofile", views.AdminProfileViewSet.as_view({"get": "list"}), name="Adminprofile"),
    path("AdminprofileUpdate", views.AdminProfileViewSet.as_view({"put": "update"}), name="AdminprofileUpdate"),
    path("validate_email", views.AdminProfileViewSet.as_view({"post": "validate"}), name="validate_email"),
    path("reset_password", views.AdminProfileViewSet.as_view({"put": "create"}), name="reset_password"),

    #Content Management
    path("Terms_and_condition", views.ContentManagementViewSet.as_view({"get": "list"}), name="Terms_and_condition"),
    path("update_content", views.ContentManagementViewSet.as_view({"put": "update"}), name="update_content"),
    path("delete_content", views.ContentManagementViewSet.as_view({"delete": "delete"}), name="delete_content"),

    path("CompanyNameView", views.CompanyNameView.as_view({"get": "create"}), name="CompanyNameView"),
    # path("Adminprofile", views.AdminProfileViewSet.as_view({"get": "list"}), name="Adminprofile"),
    # path("AdminprofileUpdate", views.AdminProfileViewSet.as_view({"get": "update"}), name="AdminprofileUpdate")

    #ManageCompany
    path("company", views.ManageCompanyView.as_view({"post": "create", "get": "search", "put": "update", "delete": "delete"}), name="AddCompany"),

    #ManageProject
    path("search_project", views.ManageProjectViewSet.as_view({"get": "search"}), name="search_project"),
    path("retereve_project/<int:pk>", views.ManageProjectViewSet.as_view({"get": "retrieve"}), name="retereve_project"),
    path("delete_project/<int:id>", views.ManageProjectViewSet.as_view({"get": "destroy"}), name="delete_project"),
    path("create_project", views.ManageProjectViewSet.as_view({"get": "create"}), name="create_project"),
    path("create_file", views.ManageProjectViewSet.as_view({"get": "file_create"}), name="create_file")


]