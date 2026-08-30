from django.conf import settings
from django.core.cache import cache
from django.db.models import Prefetch
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from draws.models import Draw, Winner
from draws.services.public_results import PUBLIC_DRAWS_CACHE_KEY

from .serializers import PublicDrawSerializer


@extend_schema(tags=('Победители',))
class PublicDrawViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = PublicDrawSerializer
    permission_classes = (AllowAny,)
    pagination_class = None

    def list(self, request, *args, **kwargs):
        payload = cache.get(PUBLIC_DRAWS_CACHE_KEY)
        if payload is None:
            payload = self.get_serializer(
                self.get_queryset(),
                many=True,
            ).data
            cache.set(
                PUBLIC_DRAWS_CACHE_KEY,
                payload,
                timeout=settings.PUBLIC_DRAWS_CACHE_TIMEOUT,
            )
        return Response(payload)

    def get_queryset(self):
        winners = Winner.objects.select_related('user__profile').order_by(
            'prize'
        )
        return (
            Draw.objects.filter(status=Draw.Status.COMPLETED)
            .prefetch_related(Prefetch('winners', queryset=winners))
            .order_by('-draw_date')
        )
