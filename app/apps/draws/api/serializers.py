from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist

from draws.models import Draw, Winner


class PublicWinnerSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    prize_code = serializers.CharField(source='prize')
    prize_name = serializers.CharField(source='get_prize_display')

    def get_name(self, obj) -> str:
        try:
            profile = obj.user.profile
        except ObjectDoesNotExist:
            return 'Участник'

        first_name = profile.first_name.strip()
        last_name = profile.last_name.strip()
        if first_name and last_name:
            return f'{first_name} {last_name[0]}.'
        return first_name or 'Участник'

    class Meta:
        model = Winner
        fields = ('name', 'prize_code', 'prize_name')


class PublicDrawSerializer(serializers.ModelSerializer):
    winners = PublicWinnerSerializer(many=True, read_only=True)

    class Meta:
        model = Draw
        fields = ('draw_date', 'winners')
