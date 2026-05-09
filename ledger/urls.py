from django.urls import path, include
from rest_framework import routers
from .views.places import PlaceViewSet
from .views.tags import TagViewSet
from .views.stores import StoreViewSet
from .views.categories import CategoryViewSet
from .views.accounts import AccountViewSet
from .views.transactions import TransactionViewSet, GetInitialTransactionDataView, ImportTransactionsView
from users.views import UserViewSet
from .views.dashboard import DashboardViewSet
from .views.reports import ReportViewSet
from .views.logs import AccountLogViewSet, TransactionLogViewSet

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
router.register(r'dashboard', DashboardViewSet, basename='dashboard')
router.register(r'reports', ReportViewSet, basename='report')
router.register(r'logs/transactions', TransactionLogViewSet, basename='transaction-log')
router.register(r'logs/accounts', AccountLogViewSet, basename='account-log')

urlpatterns = [
    path('transactions/import/', ImportTransactionsView.as_view(), name='transaction-import'),
    path('transactions/initial/list/', GetInitialTransactionDataView.as_view(), 
        name='intial-data'),
    path('', include(router.urls)),
]
