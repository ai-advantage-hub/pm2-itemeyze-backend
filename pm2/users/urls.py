from django.urls import path

from users import views

urlpatterns = [

    # Onboarding
    path("signup", views.SignUpViewSet.as_view(
        {"post": "create"}), name="signup"),
    path("resend_otp", views.ReSendOtpViewSet.as_view(
        {"post": "create"}), name="resend_otp"),
    path("verify_otp", views.VerifyOTPViewSet.as_view(
        {"post": "create"}, name="verify_otp")),
    path("login", views.UserLoginViewSet.as_view(
        {"post": "create"}, name="login")),
    path("forgot_password", views.ForgotPasswordViewSet.as_view(
        {"post": "create"}, name="forgot_password")),
    path("reset_password", views.ResetPasswordViewSet.as_view(
        {"put": "update"}, name="reset_password")),
    path("company_list", views.CompanyNameViewSet.as_view(
        {"get": "list"}, name="company_list")),

    path("welcome_name", views.UserNameViewSet.as_view(
        {"get": "get"}, name="welcome_name")),
    

    #Home
    path("create_project", views.ProjectViewSet.as_view(
        {"post": "create", "get": "search"}, name="create_project")),
    # path("add_files", views.FileDetailsViewSet.as_view(
    #     {"post": "create"}, name="add_files")),
    path("add_files", views.FileDetailsViewSet.as_view(
        {"post": "create"}, name="add_files")),
    # path("user_saved_list", views.FileDetailsViewSet.as_view(
    #     {"get": "user_saved_list"}, name="user_saved_list")),
    # path("submit_to_admin", views.FileDetailsViewSet.as_view(
    #     {"post": "submit_to_admin"}, name="submit_to_admin")),
    # path("submitted_to_admin_list", views.FileDetailsViewSet.as_view(
    #     {"get": "submitted_to_admin_list"}, name="submitted_to_admin_list")),
    path("list_files/<int:id>", views.FileDetailsViewSet.as_view(
        {"get": "list"}, name="list_files")),
    path("project_details/<int:pk>", views.ProjectDetailsViewSet.as_view(
        {"get": "list"}, name="project_details")),
    path("edit_file/<int:id>", views.EditFileViewSet.as_view(
        {"put": "update", "delete":"destroy"}, name="edit_file")),
    path("terms_and_conditions", views.TermsAndConditionsViewSet.as_view(
        {"get": "list"}, name="terms_and_conditions")),

    #Settings    
    path("view_profile", views.ViewProfileViewSet.as_view(
        {"get": "list"}, name="view_profile")),
    path("edit_profile", views.UserEditProfileViewSet.as_view(
        {"put": "update"}, name="edit_profile")),
    path("change_password", views.UserChangePasswordViewSet.as_view(
        {"put": "create"}, name="change_password")),
    path("user_listing", views.UserListingViewSet.as_view(
        {"get": "list"}, name="user_listing")),
    path("about_the_app", views.AboutAppViewset.as_view(
        {"get": "list"}, name="about_the_app")),
    path("enable_disable_notifications", views.NotificationStatusViewSet.as_view(
        {"put": "update"}, name="enable_disable_notifications")),

    #Global Search
    path("global_search", views.GlobalSearchViewSet.as_view(
        {"get": "search"}, name="global_search")),

    #FCM
    path("user_device", views.UpdateDeviceDetailViewSet.as_view(
        {'put': 'perform_update', 'get': 'retrieve', 'delete': 'perform_destroy'}), name="user_device"),

    #Notifications
    path("send_notifications", views.SendNotiticationViewSet.as_view(
        {"put": "update"}, name="send_notifications")),
    path("list_notifications", views.NotificationViewSet.as_view(
        {"get": "list"}, name="list_notifications")),
    path("notification_count", views.NotificationViewSet.as_view(
        {"get": "notification_count"}, name="notification_count")),
    path("clear_notifications", views.ClearAllNotificationViewset.as_view(
        {"put": "update"}, name="clear_notifications")),
   
    #Log out
    path("logout", views.LogoutUserViewSet.as_view(
        {"post": "post"}, name="logout")),


    #Delete Account
    path("delete_account", views.DeleteUserViewSet.as_view(
        {"put": "update"}, name="delete_account")),


    #CR2 Points
    path("user_saved_list/<int:id>", views.FileDetailsViewSet.as_view(
        {"get": "user_saved_list"}, name="user_saved_list")),
    path("submit_to_admin", views.FileDetailsViewSet.as_view(
        {"post": "submit_to_admin"}, name="submit_to_admin")),
    path("submitted_to_admin_list/<int:id>", views.FileDetailsViewSet.as_view(
        {"get": "submitted_to_admin_list"}, name="submitted_to_admin_list")),

    path("file_list/<int:id>", views.FileDetailsViewSet.as_view(
        {"get": "file_list"}, name="file_list")),

    path("manufacturer_list", views.FileDetailsViewSet.as_view(
        {"get": "manufacturer_list"}, name="manufacturer_list")),

    path("create_file", views.FileDetailsViewSet.as_view(
        {"post": "create_file"}, name="create_file")),
    
    path("update_file/<int:id>", views.EditFileViewSet.as_view(
        {"put": "update_file"}, name="update_file")),


    # path("create_and_upload_file", views.CreateFileWithImage.as_view(
    #     {"post": "create_and_upload_file"}, name="create_and_upload_file")),
    path("create_and_upload_file", views.CreateFileWithImage2.as_view(
        {"post": "create"}, name="create_and_upload_file")),

    path("create", views.CreateFileWithImage.as_view(
        {"post": "create"}, name="create")),

    
    

]