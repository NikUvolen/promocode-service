from rest_framework.routers import DefaultRouter

from .views import PromoCodeViewSet


router = DefaultRouter()
router.register('promo-codes', PromoCodeViewSet, basename='promo-code')

urlpatterns = router.urls
