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
    

    #Home
    path("create_project", views.ProjectViewSet.as_view(
        {"post": "create", "get": "search"}, name="create_project")),
    path("add_files", views.FileDetailsViewSet.as_view(
        {"post": "create", "get": "list"}, name="add_files")),
    path("project_details/<int:pk>", views.ProjectDetailsViewSet.as_view(
        {"get": "list"}, name="project_details")),
    path("edit_file/<int:pk>", views.EditFileViewSet.as_view(
        {"put": "update", "delete":"destroy"}, name="edit_file")),
    path("terms_and_conditions", views.TermsAndConditionsViewSet.as_view(
        {"get": "list"}, name="terms_and_conditions")),

    #Settings    
    path("view_profile/<int:id>", views.ViewProfileViewSet.as_view(
        {"get": "list"}, name="view_profile")),



    path("user_listing", views.UserListingViewSet.as_view(
        {"get": "list"}, name="user_listing")),
    

]