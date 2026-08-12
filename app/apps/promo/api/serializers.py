from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from promo.models import PromoCode


class PromoCodePrizeSerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()


class PromoCodeSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    prize = serializers.SerializerMethodField()

    @extend_schema_field(
        serializers.ChoiceField(
            choices=('participating', 'not_won', 'won'),
        )
    )
    def get_status(self, obj):
        if getattr(obj, 'has_won', False):
            return 'won'
        if getattr(obj, 'draw_completed', False):
            return 'not_won'
        return 'participating'

    @extend_schema_field(PromoCodePrizeSerializer(allow_null=True))
    def get_prize(self, obj):
        if not getattr(obj, 'has_won', False):
            return None
        return {
            'code': obj.winner.prize,
            'name': obj.winner.get_prize_display(),
        }

    class Meta:
        model = PromoCode
        fields = ('code', 'registered_at', 'status', 'prize')
        read_only_fields = fields


class PromoCodeRegistrationSerializer(serializers.Serializer):
    code = serializers.CharField(
        trim_whitespace=False,
        allow_blank=True,
        write_only=True,
    )


class PromoCodeErrorSerializer(serializers.Serializer):
    detail = serializers.CharField()
    reason = serializers.CharField()


class PromoCodeRateLimitSerializer(PromoCodeErrorSerializer):
    retry_after = serializers.IntegerField()
    blocked_until = serializers.DateTimeField()


class PromoCodeRegistrationStatusSerializer(serializers.Serializer):
    is_blocked = serializers.BooleanField()
    retry_after = serializers.IntegerField()
    blocked_until = serializers.DateTimeField(allow_null=True)
