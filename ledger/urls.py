from django.urls import path, include
from rest_framework import routers
from .views.places import PlaceViewSet
from .views.tags import TagViewSet

urlpatterns = []

app_name = "ledger"

router = routers.SimpleRouter()
router.register(r'places', PlaceViewSet, basename='place')
router.register(r'tags', TagViewSet, basename='tag')

urlpatterns = [
    path('', include(router.urls)),
]
urlpatterns += router.urls