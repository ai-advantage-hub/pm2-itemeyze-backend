from django.urls import path

from custom_admin import views

urlpatterns = [

    # Onboarding
    path("login", views.AdminLoginView.as_view({"post": "create"}), name="login"),
    path("forgot_password", views.ForgotPasswordViewSet.as_view({"post": "create"}), name="forgot_password"),
    path("ConfirmPassword", views.ResetPasswordViewSet.as_view({"post": "create"}), name="ConfirmPassword"),

    path("welcome_name", views.AdminNameViewset.as_view({"get": "get"}), name="welcome_name"),

    #Admin profile
    path("reset_password", views.AdminProfileViewSet.as_view({"put": "create"}), name="reset_password"),

    path("adminprofile", views.AdminProfileViewSet.as_view({"get": "list", "post": "validate", "put": "update"}), name="adminprofile"),

    #Content Management
    path("Terms_and_condition", views.ContentManagementViewSet.as_view({"get": "list"}), name="Terms_and_condition"),
    path("update_content", views.ContentManagementViewSet.as_view({"put": "update"}), name="update_content"),
    path("delete_content", views.ContentManagementViewSet.as_view({"delete": "delete"}), name="delete_content"),

    path("CompanyNameView", views.CompanyNameView.as_view({"get": "create"}), name="CompanyNameView"),

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
    # path("update_file/<int:pk>", views.ManageProjectViewSet.as_view({"put": "update_file"}), name="update_file"),
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
    path("edit_subadmin/<int:id>", views.ManageSubadminViewSet.as_view({"put": "edit_subadmin"}), name="edit_subadmin"),
    path("delete_subadmin", views.ManageSubadminViewSet.as_view({"put": "update"}), name="delete_subadmin"),


    #Dashboard
    path("admin_dashboard", views.DashBoardViewSet.as_view({"get": "get"}), name="admin_dashboard"),
    path("user_email_list", views.UseremailViewSet.as_view({"get": "get"}), name="user_email_list"),

    #Manage User
    path("manage_user_list", views.ManageUserAdminViewSet.as_view({"get": "list"}), name="manage_user_list"),
    path("change_status", views.ManageUserAdminViewSet.as_view({"put": "change_status"}), name="change_status"),
    path("user_details/<int:id>", views.ManageUserAdminViewSet.as_view({"get": "retrieve"}), name="user_details"),
    path("unapproved_users", views.ManageUserAdminViewSet.as_view({"get": "unapproved_users"}), name="unapproved_users"),
    path("unapproved_users_count", views.ManageUserAdminViewSet.as_view({"get": "unapproved_users_count"}), name="unapproved_users_count"),
    path("approve_users", views.ManageUserAdminViewSet.as_view({"put": "approve_users"}), name="approve_users"),
    path("project_list/<int:id>", views.ManageUserAdminViewSet.as_view({"get": "project_list"}), name="project_list"),
    path("retrieve_user_project/<int:pk>", views.ManageUserAdminViewSet.as_view({"get": "retrieve_user_project"}), name="retrieve_user_project"),
    path("delete_user_admin/<int:id>", views.ManageUserAdminViewSet.as_view({"delete": "delete_user_admin"}), name="delete_user_admin"),
    path("view_file_admin/<int:id>", views.ManageUserAdminViewSet.as_view({"get": "view_file_admin"}), name="view_file_admin"),
    path("delete_file_user/<int:id>", views.ManageUserAdminViewSet.as_view({"delete": "delete_file_user"}), name="delete_file_user"),
    path("admin_user_csv/<int:pk>/download_csv/", views.ManageUserAdminViewSet.as_view({"get": "admin_user_csv"}), name="admin_user_csv"),
    path("project/remove-user/", views.ManageUserAdminViewSet.as_view({"delete": "remove_user_from_project"}), name="remove_user_from_project"),
    path("update_file_admin/<int:pk>", views.ManageUserAdminViewSet.as_view({"put": "update_file_admin"}), name="update_file_admin"),
    path("project_graph/<int:id>", views.ManageUserAdminViewSet.as_view({"get": "project_graph"}), name="project_graph"),

    #CR Points
    path("list_deleted_projects", views.DeletedProjectsViewSet.as_view({"get": "list"}), name="list_deleted_projects"),
    path("restore_project/<int:id>", views.DeletedProjectsViewSet.as_view({"put": "restore"}), name="restore_project"),
    path("list_deleted_files/<int:id>", views.DeletedFilesViewSet.as_view({"get": "list"}), name="list_deleted_files"),
    path("restore_files", views.DeletedFilesViewSet.as_view({"put": "restore"}), name="restore_files"),

    path("approve_user", views.EditUserCompanyViewSet.as_view({"put": "approve_user"}), name="approve_user"),

    path("company_status", views.DeactivateCompanyViewSet.as_view({"put": "update"}), name="company_status"),


    path("users_listing", views.UserListingViewSet.as_view({"get": "list"}), name="users_listing"),


    #CR2 Points
    path("approved_files_list/<int:id>", views.ApprovedFilesListingViewSet.as_view({"get": "approved_files_list"}), name="approved_files_list"),

    path("disapprove_file", views.DisapproveFileViewSet.as_view({"put": "disapprove_file"}), name="disapprove_file"),
    path("list_disapproved_file/<int:id>", views.DisapproveFileViewSet.as_view({"get": "list_disapproved_file"}), name="list_disapproved_file"),
    path("view_disapproved_file/<int:id>", views.DisapproveFileViewSet.as_view({"get": "view_disapproved_file"}), name="view_disapproved_file"),
    path("approve", views.DisapproveFileViewSet.as_view({"put": "approve"}), name="approve"),

    path("marked_for_delete_files/<int:id>", views.MarkedForDeletedFilesViewSet.as_view({"get": "list"}), name="marked_for_delete_files"),
    path("approve_marked_for_deleted_file", views.MarkedForDeletedFilesViewSet.as_view({"put": "approve"}), name="approve_marked_for_deleted_file"),

    path("edit_user_details/<int:id>", views.EditUserDetailsViewSet.as_view({"put": "update"}), name="edit_user_details"),

    path("unapproved_users_list", views.UnapprovedUsersViewSet.as_view({"get": "unapproved_users_list"}), name="unapproved_users_list"),
    path("approve_requested_user", views.UnapprovedUsersViewSet.as_view({"put": "approve_requested_user"}), name="approve_requested_user"),

    path("project_create", views.ProjectViewSet.as_view({"post": "create"}), name="project_create"),
    path("project_list", views.ProjectViewSet.as_view({"get": "project_list"}), name="project_list"),
    path("project_details/<int:pk>", views.ProjectViewSet.as_view({"get": "project_details"}), name="project_details"),
    path("project_approve", views.ProjectViewSet.as_view({"put": "project_approve"}), name="project_approve"),

    path("create_manufacturer", views.ManageManufacturerNameViewSet.as_view({"post": "create"}), name="create_manufacturer"),
    path("edit_manufacturer", views.ManageManufacturerNameViewSet.as_view({"put": "update"}), name="edit_manufacturer"),
    path("view_manufacturer/<int:id>", views.ManageManufacturerNameViewSet.as_view({"get": "retrieve"}), name="view_manufacturer"),
    path("manufacturer_list", views.ManageManufacturerNameViewSet.as_view({"get": "manufacturer_list"}), name="manufacturer_list"),
    path("delete_manufacturer", views.ManageManufacturerNameViewSet.as_view({"delete": "delete_manufacturer"}), name="delete_manufacturer"),

    path("users_list_of_company/<int:id>", views.AssignToUsersViewSet.as_view({"get": "users_list"}), name="users_list_of_company"),

    path("list_manufacturer", views.FilesViewSet.as_view({"get": "list_manufacturer"}), name="list_manufacturer"),
    path("create_file_admin", views.FilesViewSet.as_view({"post": "create_file_admin"}), name="create_file_admin"),
    path("update_file/<int:id>", views.FilesViewSet.as_view({"put": "update_file"}), name="update_file"),

    path("company_list", views.CompanyManufacturerListViewSet.as_view({"get": "company_list"}), name="company_list"),
    path("manufacturer_listing", views.CompanyManufacturerListViewSet.as_view({"get": "manufacturer_listing"}), name="manufacturer_listing"),



    path("upload_excel_data", views.UploadexcelViewSet.as_view({"post": "create"}), name="upload_excel_data"),

    #TotalUsers
    path("total_users", views.TotalUserCountViewSet.as_view({"get": "list"}), name="total_users"),

]