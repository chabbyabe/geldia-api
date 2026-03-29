from django.urls import path, include
from rest_framework import routers
from .views.places import PlaceViewSet
from .views.tags import TagViewSet
from .views.stores import StoreViewSet
from .views.categories import CategoryViewSet

urlpatterns = []

app_name = "ledger"

router = routers.SimpleRouter()
router.register(r'places', PlaceViewSet, basename='place')
router.register(r'tags', TagViewSet, basename='tag')
router.register(r'stores', StoreViewSet, basename='store')
router.register(r'categories', CategoryViewSet, basename='category')

urlpatterns = [
    path('', include(router.urls)),
]
urlpatterns += router.urls