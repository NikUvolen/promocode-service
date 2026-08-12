from rest_framework import serializers

from promo.models import PromoCode


class PromoCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromoCode
        fields = ('code', 'registered_at')
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
