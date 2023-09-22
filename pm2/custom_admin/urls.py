from django.urls import path

from custom_admin import views

urlpatterns = [

    # Onboarding
    path("login", views.AdminLoginView.as_view({"post": "create"}), name="login"),
    path("forgot_password", views.ForgotPasswordViewSet.as_view({"post": "create"}), name="forgot_password"),
    path("ConfirmPassword", views.ResetPasswordViewSet.as_view({"post": "create"}), name="ConfirmPassword"),

    path("welcome_name", views.AdminNameViewset.as_view({"get": "get"}), name="welcome_name"),

    #Admin profile

    # path("Adminprofile", views.AdminProfileViewSet.as_view({"get": "list"}), name="Adminprofile"),
    # path("AdminprofileUpdate", views.AdminProfileViewSet.as_view({"put": "update"}), name="AdminprofileUpdate"),
    # path("validate_email", views.AdminProfileViewSet.as_view({"post": "validate"}), name="validate_email"),
    path("reset_password", views.AdminProfileViewSet.as_view({"put": "create"}), name="reset_password"),

    path("adminprofile", views.AdminProfileViewSet.as_view({"get": "list", "post": "validate", "put": "update"}), name="adminprofile"),

    #Content Management
    path("Terms_and_condition", views.ContentManagementViewSet.as_view({"get": "list"}), name="Terms_and_condition"),
    path("update_content", views.ContentManagementViewSet.as_view({"put": "update"}), name="update_content"),
    path("delete_content", views.ContentManagementViewSet.as_view({"delete": "delete"}), name="delete_content"),

    path("CompanyNameView", views.CompanyNameView.as_view({"get": "create"}), name="CompanyNameView"),
    # path("Adminprofile", views.AdminProfileViewSet.as_view({"get": "list"}), name="Adminprofile"),
    # path("AdminprofileUpdate", views.AdminProfileViewSet.as_view({"get": "update"}), name="AdminprofileUpdate")

    #ManageCompany
    path("company", views.ManageCompanyView.as_view({"post": "create", "get": "search", "put": "update", "delete": "delete"}), name="AddCompany"),
    path("status", views.ManageCompanyView.as_view({"post": "status"}), name="status"),

    #ManageProject
    path("search_project", views.ManageProjectViewSet.as_view({"get": "search"}), name="search_project"),
    path("retrieve_project/<int:pk>", views.ManageProjectViewSet.as_view({"get": "retrieve"}), name="retereve_project"),
    path("delete_project/<int:id>", views.ManageProjectViewSet.as_view({"delete": "destroy"}), name="delete_project"),
    path("create_project", views.ManageProjectViewSet.as_view({"post": "create"}), name="create_project"),
    path("create_file", views.ManageProjectViewSet.as_view({"post": "file_create"}), name="create_file"),
    path("un_approved_project", views.ManageProjectViewSet.as_view({"get": "un_approved_project"}), name="un_approved_project"),
    path("un_approved_project_count", views.ManageProjectViewSet.as_view({"get": "un_approved_project_count"}), name="un_approved_project_count"),
    path("approve_project", views.ManageProjectViewSet.as_view({"put": "approve_project"}), name="approve_project"),
    path("un_approved_file/<int:id>", views.ManageProjectViewSet.as_view({"get": "un_approved_file"}), name="un_approved_file"),
    path("un_approved_files_count/<int:id>", views.ManageProjectViewSet.as_view({"get": "un_approved_files_count"}), name="un_approved_files_count"),
    path("view_file/<int:id>", views.ManageProjectViewSet.as_view({"get": "view_file"}), name="view_file"),
    path("destroy_file/<int:id>", views.ManageProjectViewSet.as_view({"delete": "destroy_file"}), name="destroy_file"),
    path("update_file/<int:pk>", views.ManageProjectViewSet.as_view({"put": "update_file"}), name="update_file"),
    path("approve_file", views.ManageProjectViewSet.as_view({"put": "approve_file"}), name="approve_file"),
    path("delete_file_list/<int:id>", views.ManageProjectViewSet.as_view({"get": "delete_file_list"}), name="delete_file_list"),
    path("delete_file_admin", views.ManageProjectViewSet.as_view({"delete": "delete_file_admin"}), name="delete_file_admin"),
    path("view_file_unapproved/<int:id>", views.ManageProjectViewSet.as_view({"get": "view_file_unapproved"}), name="view_file_unapproved"),
    path("project/<int:pk>/download_csv/", views.ManageProjectViewSet.as_view({"get": "save_to_csv"}), name="save_to_csv"),

    #ManageSubAdmin
    path("search_sub_admin", views.ManageSubadminViewSet.as_view({"get": "search"}), name="search_sub_admin"),
    path("retrieve_sub_admin/<int:id>", views.ManageSubadminViewSet.as_view({"get": "retrieve"}), name="retrieve_sub_admin"),
    path("subadmin_status", views.ManageSubadminViewSet.as_view({"put": "subadmin_status"}), name="subadmin_status"),
    path("create_subadmin", views.ManageSubadminViewSet.as_view({"post": "create"}), name="create_subadmin"),


    #Dashboard
    path("admin_dashboard", views.DashBoardViewSet.as_view({"get": "get"}), name="admin_dashboard"),
    path("user_email_list", views.UseremailViewSet.as_view({"get": "get"}), name="user_email_list"),

    


]