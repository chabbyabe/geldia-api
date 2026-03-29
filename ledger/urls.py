from django.urls import path, include
from rest_framework import routers

urlpatterns = []

app_name = "ledger"

router = routers.SimpleRouter()
urlpatterns = [
    path('', include(router.urls)),
]
urlpatterns += router.urls
