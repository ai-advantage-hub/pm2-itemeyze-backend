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
        {"post" : "create"}, name="reset_password")),

]