from django.urls import path

from users import views

urlpatterns = [

    # Onboarding
    path("signup", views.SignUpViewSet.as_view(
        {"post": "create"}), name="signup"),
    path("resend_otp", views.ReSendOtpViewSet.as_view(
        {"post": "create"}), name="resend_otp"),
    path("verify_otp", views.VerifyOTPViewSet.as_view(
        {"post" : "create"}, name="verify_otp")),
    path("login", views.UserLoginViewSet.as_view(
        {"post" : "create"}, name="login")),
    path("forgot_password", views.ForgotPasswordViewSet.as_view(
        {"post" : "create"}, name="forgot_password")),
    path("reset_password", views.ResetPasswordViewSet.as_view(
        {"put" : "update"}, name="reset_password")),

    #Home
    path("create_project", views.CreateProjectViewSet.as_view(
        {"post" : "create"}, name="create_project")),
    path("list_project", views.ListProjectViewSet.as_view(
        {"get" : "list"}, name="list_project")),
    path("search_project", views.ListProjectViewSet.as_view(
        {"get" : "search"}, name="search_project")),
    path("add_files", views.CreateFileDetailsViewSet.as_view(
        {"post" : "create"}, name="add_files")),
    path("list_files", views.ListFileDetailsViewSet.as_view(
        {"get" : "list"}, name="list_files")),
    path("project_details/<int:pk>", views.ProjectDetailsViewSet.as_view(
        {"get" : "list"}, name="project_details")),

]