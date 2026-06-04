from django.urls import include, path
from dj_rest_auth.views import (
    LoginView,
    LogoutView,
    UserDetailsView,
)
from rest_framework_simplejwt.views import TokenVerifyView
from users.views import (
    CompanyViewSet,
    ForgotPasswordRequestView,
    ManualRegistrationVerificationView,
    ManualPasswordChangeVerificationView,
    UserSettingsViewSet,
    PasswordChangeRequestView,
    UserRegisterView,
    VerifyPasswordChangeView,
    VerifyRegistrationView,
)
from rest_framework import routers
urlpatterns = []

dj_rest_auth_urls = [
    path("login/", LoginView.as_view(), name="rest_login"),
    path("logout/", LogoutView.as_view(), name="rest_logout"),
    path("user/", UserDetailsView.as_view(), name="rest_user_details"),
    path("password/change/", PasswordChangeRequestView.as_view(),
         name="rest_password_change"),
    path("password/forgot/", ForgotPasswordRequestView.as_view(),
         name="rest_password_forgot"),
    path("password/change/verify/", VerifyPasswordChangeView.as_view(),
         name="rest_password_change_verify"),
    path("password/change/manual-verify/", 
         ManualPasswordChangeVerificationView.as_view(),
         name="rest_password_change_manual_verify"),
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),
]

auth_urls = [
    path("auth/", include(dj_rest_auth_urls)),
    path("auth/register", UserRegisterView.as_view(), name="rest_register"),
    path("auth/register/verify/", VerifyRegistrationView.as_view(),
         name="rest_register_verify"),
    path("auth/email/verify/", VerifyRegistrationView.as_view(),
         name="rest_email_verify"),
    path("auth/email/manual-verify/",
         ManualRegistrationVerificationView.as_view(),
         name="rest_email_manual_verify"),
]

router = routers.SimpleRouter()
router.register(r'settings', UserSettingsViewSet, basename='settings')
router.register(r'settings/companies', CompanyViewSet, basename='company')

urlpatterns = [
    path('', include(router.urls)),
]

urlpatterns += auth_urls
