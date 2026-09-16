from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.utils import timezone
from datetime import timedelta


class OfflineTokenObtainPairSerializer(TokenObtainPairSerializer):
    """JWT usado pelo PWA. O login online continua obrigatório."""

    def validate(self, attrs):
        data = super().validate(attrs)
        agora = timezone.now()
        refresh = self.get_token(self.user)
        refresh['user_id'] = self.user.pk
        refresh['username'] = self.user.get_username()
        refresh['login_em'] = int(agora.timestamp())

        data['refresh'] = str(refresh)
        data['access'] = str(refresh.access_token)
        data['user_id'] = self.user.pk
        data['username'] = self.user.get_username()
        data['login_em'] = agora.isoformat()
        data['expira_em'] = (agora + timedelta(hours=5)).isoformat()
        return data


class SyncOperationInputSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    tipo = serializers.CharField(max_length=60)
    lote = serializers.CharField(max_length=100, allow_blank=True, required=False)
    estoque_id = serializers.IntegerField(required=False, allow_null=True)
    quantidade = serializers.DecimalField(max_digits=14, decimal_places=2, required=False)
    base_lote_versao = serializers.IntegerField(min_value=0, default=0)
    criado_local_em = serializers.DateTimeField(required=False, allow_null=True)
    payload = serializers.JSONField(required=False, default=dict)


class SyncBatchSerializer(serializers.Serializer):
    device_id = serializers.CharField(max_length=120)
    operacoes = SyncOperationInputSerializer(many=True)
