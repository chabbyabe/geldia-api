from django.urls import path, include
from rest_framework import routers
from .views.places import PlaceViewSet
from .views.tags import TagViewSet
from .views.stores import StoreViewSet
from .views.categories import CategoryViewSet
from .views.accounts import AccountViewSet
from .views.transactions import TransactionViewSet, GetInitialTransactionDataView
from users.views import UserViewSet

urlpatterns = []

app_name = "ledger"

router = routers.SimpleRouter()
router.register(r'places', PlaceViewSet, basename='place')
router.register(r'tags', TagViewSet, basename='tag')
router.register(r'stores', StoreViewSet, basename='store')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'accounts', AccountViewSet, basename='account')
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    path('', include(router.urls)),
    path('transactions/initial/list/', GetInitialTransactionDataView.as_view(), 
        name='intial-data'),
]
urlpatterns += router.urls