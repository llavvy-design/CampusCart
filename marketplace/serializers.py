
from rest_framework import serializers

from payments.services.mpesa import normalize_mpesa_phone


class CheckoutSerializer(serializers.Serializer):
    phone_number = serializers.CharField(
        max_length=20,
        required=True
    )

    def validate_phone_number(self, value):
        try:
            return normalize_mpesa_phone(value)
        except ValueError as error:
            raise serializers.ValidationError(str(error))
