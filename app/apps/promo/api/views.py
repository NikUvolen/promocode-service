from django.db.models import Exists, OuterRef
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from draws.models import Draw, Winner
from promo.models import PromoCode
from promo.services.registration import (
    ProfileIncomplete,
    PromoCodeRateLimited,
    PromoCodeRegistrationError,
    get_registration_status,
    register_promo_code,
)

from .serializers import (
    PromoCodeErrorSerializer,
    PromoCodeRateLimitSerializer,
    PromoCodeRegistrationSerializer,
    PromoCodeRegistrationStatusSerializer,
    PromoCodeSerializer,
)
from .throttles import PromoCodeRegisterRateThrottle


class PromoCodePagination(PageNumberPagination):
    page_size = 10
    max_page_size = 100


class PromoCodeViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = PromoCodeSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = PromoCodePagination

    def get_queryset(self):
        return (
            PromoCode.objects.filter(registered_by=self.request.user)
            .annotate(
                has_won=Exists(
                    Winner.objects.filter(promo_code_id=OuterRef('pk'))
                ),
                draw_completed=Exists(
                    Draw.objects.filter(
                        status=Draw.Status.COMPLETED,
                        period_started_at__lte=OuterRef('registered_at'),
                        period_ended_at__gt=OuterRef('registered_at'),
                    )
                ),
            )
            .select_related('winner')
            .order_by('-registered_at')
        )

    @extend_schema(
        tags=('Промокоды',),
        responses={200: PromoCodeRegistrationStatusSerializer},
    )
    @action(
        detail=False,
        methods=('get',),
        url_path='registration-status',
    )
    def registration_status(self, request):
        return Response(get_registration_status(user=request.user))

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
    @action(
        detail=False,
        methods=('post',),
        throttle_classes=(PromoCodeRegisterRateThrottle,),
    )
    def register(self, request):
        serializer = PromoCodeRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            promo_code = register_promo_code(
                user=request.user,
                raw_code=serializer.validated_data['code'],
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
            PromoCodeSerializer(
                promo_code,
                context=self.get_serializer_context(),
            ).data,
            status=status.HTTP_201_CREATED,
        )
