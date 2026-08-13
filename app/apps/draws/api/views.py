from django.db.models import Prefetch
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework.permissions import AllowAny

from draws.models import Draw, Winner

from .serializers import PublicDrawSerializer


@extend_schema(tags=('Победители',))
class PublicDrawViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = PublicDrawSerializer
    permission_classes = (AllowAny,)
    pagination_class = None

    def get_queryset(self):
        winners = Winner.objects.select_related('user__profile').order_by(
            'prize'
        )
        return (
            Draw.objects.filter(status=Draw.Status.COMPLETED)
            .prefetch_related(Prefetch('winners', queryset=winners))
            .order_by('-draw_date')
        )
