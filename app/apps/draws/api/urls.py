from rest_framework.routers import DefaultRouter

from .views import PublicDrawViewSet


router = DefaultRouter()
router.register('draws', PublicDrawViewSet, basename='public-draw')

urlpatterns = router.urls
