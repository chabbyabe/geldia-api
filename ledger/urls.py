from django.urls import path, include
from rest_framework import routers
from .views.places import PlaceViewSet

urlpatterns = []

app_name = "ledger"

router = routers.SimpleRouter()
router.register(r'places', PlaceViewSet, basename='place')

urlpatterns = [
    path('', include(router.urls)),
]
urlpatterns += router.urls