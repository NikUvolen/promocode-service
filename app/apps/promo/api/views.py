from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from promo.models import PromoCode
from promo.services.registration import (
    ProfileIncomplete,
    PromoCodeRateLimited,
    PromoCodeRegistrationError,
    register_promo_code,
)

from .serializers import (
    PromoCodeErrorSerializer,
    PromoCodeRateLimitSerializer,
    PromoCodeRegistrationSerializer,
    PromoCodeSerializer,
)


class PromoCodePagination(PageNumberPagination):
    page_size = 20
    max_page_size = 100


class PromoCodeViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = PromoCodeSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = PromoCodePagination

    def get_queryset(self):
        return PromoCode.objects.filter(
            registered_by=self.request.user,
        ).order_by('-registered_at')

    @extend_schema(
        tags=('Промокоды',),
        request=PromoCodeRegistrationSerializer,
        responses={
            201: PromoCodeSerializer,
            400: PromoCodeErrorSerializer,
            409: PromoCodeErrorSerializer,
            429: PromoCodeRateLimitSerializer,
        },
    )
    @action(detail=False, methods=('post',))
    def register(self, request):
        serializer = PromoCodeRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            promo_code = register_promo_code(
                user=request.user,
                raw_code=serializer.validated_data['code'],
                ip_address=request.META.get('REMOTE_ADDR'),
            )
        except PromoCodeRateLimited as exc:
            return Response(
                {
                    'detail': exc.message,
                    'reason': exc.reason,
                    'retry_after': exc.retry_after,
                    'blocked_until': exc.blocked_until,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        except ProfileIncomplete as exc:
            return Response(
                {'detail': exc.message, 'reason': exc.reason},
                status=status.HTTP_409_CONFLICT,
            )
        except PromoCodeRegistrationError as exc:
            return Response(
                {'detail': exc.message, 'reason': exc.reason},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            PromoCodeSerializer(promo_code).data,
            status=status.HTTP_201_CREATED,
        )
